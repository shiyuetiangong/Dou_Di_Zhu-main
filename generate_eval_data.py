import argparse
import pickle
import numpy as np

# 数字代表牌面大小，3-10为数字牌，11-13为JQK，14为A，17为2，20为小王，30为大王
# EnvCard2RealCard = {3: '3', 4: '4', 5: '5', 6: '6', 7: '7',
#                     8: '8', 9: '9', 10: '10', 11: 'J', 12: 'Q',
#                     13: 'K', 14: 'A', 17: '2', 20: 'X', 30: 'D'}

deck = []
for i in range(3, 15):
    deck.extend([i for _ in range(4)])
deck.extend([17 for _ in range(4)])
deck.extend([20, 30])

def get_parser():
    parser = argparse.ArgumentParser(description='DouZero: random data generator')
    parser.add_argument('--output', default='eval_data', type=str)
    parser.add_argument('--num_games', default=1000, type=int) # 生成多少副牌
    return parser

 # 随机生成一副牌   
def generate():
    _deck = deck.copy()
    np.random.shuffle(_deck)
    card_play_data = {'landlord': _deck[:20],
                      'landlord_up': _deck[20:37],
                      'landlord_down': _deck[37:54],
                      'three_landlord_cards': _deck[17:20],
                      }
    for key in card_play_data:
        card_play_data[key].sort()
    return card_play_data

# 生成指定牌型
def generate_fixed():
    card_play_datas = [{'landlord': [3,3,3,3,4,7,7,7,5,5,5,5,6,13,13,13,17],
                      'landlord_up': [4,4,4,6,6,6,7,8,8,8,8,9,10,10,10,10,17],
                      'landlord_down': [9,9,9,11,11,11,11,12,12,12,12,13,14,14,14,14,17],
                      'three_landlord_cards': [17, 20, 30],
                      'actions':{
                          'landlord':[[3,3,3,3],[],[]],
                          'landlord_up':[[],[],[]],
                          'landlord_down':[[11,11,11,11],[17],[12,12]]
                      }
                      }]
    for card_play_data in card_play_datas:
        for key in card_play_data:
            if key != 'actions':
                card_play_data[key].sort()
    return card_play_datas


if __name__ == '__main__':
    flags = get_parser().parse_args()
    output_pickle = flags.output + '.pkl'
    is_random_cards = True
    print("output_pickle:", output_pickle)
    print("generating data...")

    data = []
    if is_random_cards:
        for _ in range(flags.num_games):
            data.append(generate())
    else:
        data.extend(generate_fixed())
    print("saving pickle file...")
    with open(output_pickle,'wb') as g:
        pickle.dump(data,g,pickle.HIGHEST_PROTOCOL)




