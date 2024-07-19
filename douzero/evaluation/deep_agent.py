import torch
import numpy as np

from douzero.env.env import get_obs

def _load_model(position, model_path):
    from douzero.dmc.models import model_dict
    model = model_dict[position]()
    model_state_dict = model.state_dict()
    if torch.cuda.is_available():
        pretrained = torch.load(model_path, map_location='cuda:0')
    else:
        pretrained = torch.load(model_path, map_location='cpu')
    pretrained = {k: v for k, v in pretrained.items() if k in model_state_dict}
    model_state_dict.update(pretrained)
    model.load_state_dict(model_state_dict)
    if torch.cuda.is_available():
        model.cuda()
    model.eval()
    return model

class DeepAgent:

    def __init__(self, position, model_path):
        self.model = _load_model(position, model_path)
        self.position = position
        self.is_show_winrate = False
    def act(self, infoset):
        if len(infoset.legal_actions) == 1:
            return infoset.legal_actions[0]

        obs = get_obs(infoset) 

        z_batch = torch.from_numpy(obs['z_batch']).float()
        x_batch = torch.from_numpy(obs['x_batch']).float()
        if torch.cuda.is_available():
            z_batch, x_batch = z_batch.cuda(), x_batch.cuda()
        y_pred = self.model.forward(z_batch, x_batch, return_value=True)['values']
        y_pred = y_pred.detach().cpu().numpy()
        best_action_index = np.argmax(y_pred, axis=0)[0]
        #找到前k个最大值的索引
        k = 3
        action_indexs = np.argsort(y_pred, axis=0)[-k:]
        if self.is_show_winrate: 
            print(f"current player : {self.position}")
            for i in range(len(action_indexs)):
                action = infoset.legal_actions[action_indexs[i][0]]
                winrate = self.get_win_rate(y_pred[action_indexs[i][0]][0])
                print(f"action:{action} winrate:{winrate}")
            print(f"best action:{infoset.legal_actions[best_action_index]} value:{self.get_win_rate(y_pred[best_action_index][0])}")
            print("---------------------")
        best_action = infoset.legal_actions[best_action_index]
        return best_action
    
    def get_win_rate(self, confidence):
        win_rate = max(confidence, -1)
        win_rate = min(win_rate, 1)
        return str(round((win_rate + 1) / 2, 4))
