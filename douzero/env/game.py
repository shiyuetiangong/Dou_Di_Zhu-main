from copy import deepcopy
from . import move_detector as md, move_selector as ms
from .move_generator import MovesGener
import json
import os
EnvCard2RealCard = {3: '3', 4: '4', 5: '5', 6: '6', 7: '7',
                    8: '8', 9: '9', 10: '10', 11: 'J', 12: 'Q',
                    13: 'K', 14: 'A', 17: '2', 20: 'X', 30: 'D'}

RealCard2EnvCard = {'3': 3, '4': 4, '5': 5, '6': 6, '7': 7,
                    '8': 8, '9': 9, '10': 10, 'J': 11, 'Q': 12,
                    'K': 13, 'A': 14, '2': 17, 'X': 20, 'D': 30}

bombs = [[3, 3, 3, 3], [4, 4, 4, 4], [5, 5, 5, 5], [6, 6, 6, 6],
         [7, 7, 7, 7], [8, 8, 8, 8], [9, 9, 9, 9], [10, 10, 10, 10],
         [11, 11, 11, 11], [12, 12, 12, 12], [13, 13, 13, 13], [14, 14, 14, 14],
         [17, 17, 17, 17], [20, 30]]

class GameEnv(object):

    def __init__(self, players):

        self.card_play_action_seq = []

        self.three_landlord_cards = None
        self.game_over = False

        self.acting_player_position = None
        self.player_utility_dict = None

        self.players = players

        self.setp_flag = False

        self.last_move_dict = {'landlord_down': [],
                               'landlord_up': [],
                               'landlord': []}

        self.played_cards = {'landlord': [],
                             'landlord_up': [],
                             'landlord_down': []}
    
        self.player_origin_cards = {'landlord': [],
                                    'landlord_up': [],
                                    'landlord_down': []}

        self.last_move = []
        self.last_two_moves = []

        self.num_wins = {'landlord': 0,
                         'farmer': 0}

        self.num_scores = {'landlord': 0,
                           'farmer': 0}

        self.info_sets = {'landlord': InfoSet('landlord'),
                         'landlord_up': InfoSet('landlord_up'),
                         'landlord_down': InfoSet('landlord_down')}

        self.bomb_num = 0
        self.last_pid = 'landlord'
        #全局变量，记录各方最想出的牌
        self.most_wanted_card = {
            'landlord': [],
            'landlord_up': [],
            'landlord_down': []
        }
        #触发记录最想要的牌的手牌阈值
        self.trigger_threshold = 5

    def card_play_init(self, card_play_data):
        self.info_sets['landlord'].player_hand_cards = \
            card_play_data['landlord']
        self.info_sets['landlord_up'].player_hand_cards = \
            card_play_data['landlord_up']
        self.info_sets['landlord_down'].player_hand_cards = \
            card_play_data['landlord_down']
        self.player_origin_cards['landlord'] = card_play_data['landlord'][:]
        self.player_origin_cards['landlord_up'] = card_play_data['landlord_up'][:]
        self.player_origin_cards['landlord_down'] = card_play_data['landlord_down'][:]
        self.three_landlord_cards = card_play_data['three_landlord_cards']
        self.get_acting_player_position()
        self.game_infoset = self.get_infoset()

    def game_done(self):
        if len(self.info_sets['landlord'].player_hand_cards) == 0 or \
                len(self.info_sets['landlord_up'].player_hand_cards) == 0 or \
                len(self.info_sets['landlord_down'].player_hand_cards) == 0:
            # if one of the three players discards his hand,
            # then game is over.
            self.compute_player_utility()
            self.update_num_wins_scores()

            self.game_over = True
            # 写入原始手牌
            if self.setp_flag:
                log_path = 'log_'+str(os.getpid())+'.txt'
                log_path = os.path.join('log',log_path)
                with open(log_path,'a') as f:
                    f.write('------------------\n')
                    # f.write('game over\n')
                    # 原始手牌
                    f.write(f"player_origin_cards:{self.player_origin_cards}\n")
                    f.write('------------------\n')

            


    def compute_player_utility(self):

        if len(self.info_sets['landlord'].player_hand_cards) == 0:
            self.player_utility_dict = {'landlord': 2,
                                        'farmer': -1}
        else:
            self.player_utility_dict = {'landlord': -2,
                                        'farmer': 1}

    def update_num_wins_scores(self):
        for pos, utility in self.player_utility_dict.items():
            base_score = 2 if pos == 'landlord' else 1
            if utility > 0:
                self.num_wins[pos] += 1
                self.winner = pos
                self.num_scores[pos] += base_score * (2 ** self.bomb_num)
            else:
                self.num_scores[pos] -= base_score * (2 ** self.bomb_num)

    def get_winner(self):
        return self.winner

    def get_bomb_num(self):
        return self.bomb_num
    
    # 获取下家农民的最想要的牌，并检测自己能递牌的action
    def get_most_wanted_card_action(self):
        # 因为暂时不考虑给地主递牌，所以只考虑下家农民
        if self.acting_player_position == 'landlord_up':
            return []
        if self.acting_player_position == 'landlord':
            return []
        if self.acting_player_position == 'landlord_down':
            # 获取下家农民的最想要的牌
            temp_moves = self.most_wanted_card['landlord_up'][:]
            #检测是否能够递牌
            put_card_actions = list()
            for temp_move in temp_moves:
                temp_move_type = md.get_move_type(temp_move)
                if temp_move_type['type'] == md.TYPE_4_BOMB or temp_move_type['type'] == md.TYPE_5_KING_BOMB:
                    return [[]]
                for legal_move in self.game_infoset.legal_actions:
                    legal_move_type = md.get_move_type(legal_move)
                    if temp_move_type['type'] == legal_move_type['type']:
                        put_card_actions.extend(
                            self.get_legal_put_card_actions(
                                temp_move_type['type'], temp_move, legal_move))
            return put_card_actions
        # rival_move 表示本次要递的牌，move表示下家想打的手牌
    def get_legal_put_card_actions(self,rival_move_type,move,rival_move):
        moves = list()
        all_moves = []
        all_moves.append(move)
        if rival_move_type == md.TYPE_0_PASS:
            pass
        elif rival_move_type == md.TYPE_1_SINGLE:
            moves = ms.filter_type_1_single(all_moves, rival_move)

        elif rival_move_type == md.TYPE_2_PAIR:
            moves = ms.filter_type_2_pair(all_moves, rival_move)

        elif rival_move_type == md.TYPE_3_TRIPLE:
            moves = ms.filter_type_3_triple(all_moves, rival_move)

        elif rival_move_type == md.TYPE_4_BOMB:
            moves = ms.filter_type_4_bomb(all_moves, rival_move)

        elif rival_move_type == md.TYPE_5_KING_BOMB:
            moves = []

        elif rival_move_type == md.TYPE_6_3_1:
            moves = ms.filter_type_6_3_1(all_moves, rival_move)

        elif rival_move_type == md.TYPE_7_3_2:
            moves = ms.filter_type_7_3_2(all_moves, rival_move)

        elif rival_move_type == md.TYPE_8_SERIAL_SINGLE:
            moves = ms.filter_type_8_serial_single(all_moves, rival_move)

        elif rival_move_type == md.TYPE_9_SERIAL_PAIR:
            moves = ms.filter_type_9_serial_pair(all_moves, rival_move)

        elif rival_move_type == md.TYPE_10_SERIAL_TRIPLE:
            moves = ms.filter_type_10_serial_triple(all_moves, rival_move)

        elif rival_move_type == md.TYPE_11_SERIAL_3_1:
            moves = ms.filter_type_11_serial_3_1(all_moves, rival_move)

        elif rival_move_type == md.TYPE_12_SERIAL_3_2:
            moves = ms.filter_type_12_serial_3_2(all_moves, rival_move)

        elif rival_move_type == md.TYPE_13_4_2:
            moves = ms.filter_type_13_4_2(all_moves, rival_move)

        elif rival_move_type == md.TYPE_14_4_22:
            moves = ms.filter_type_14_4_22(all_moves, rival_move)

        if len(moves) > 0:
            return [rival_move]
        return []
        # if rival_move_type not in [md.TYPE_0_PASS,
        #                            md.TYPE_4_BOMB, md.TYPE_5_KING_BOMB]:
        #     moves = moves + mg.gen_type_4_bomb() + mg.gen_type_5_king_bomb()

        # if len(rival_move) != 0:  # rival_move is not 'pass'
        #     moves = moves + [[]]
        # for m in moves:
        #     m.sort()
        # return moves


    def step(self,action = None,flag = False):
        if action == None:
            action = self.players[self.acting_player_position].act(
                self.game_infoset)
        # print(f"acting_player_position:{self.acting_player_position}")
        # print(f"action:{action}")
        # print(f"legal actions : {self.game_infoset.legal_actions}")
        # print('------------------')
        assert action in self.game_infoset.legal_actions
        # 训练时不运行此配合策略
        if flag and len(self.most_wanted_card["landlord_up"]) > 0 and self.acting_player_position == 'landlord_down':
            # 是否先压死地主，在递牌?
            rival_move = self.card_play_action_seq[-1]
            landlord_up_last_move = self.card_play_action_seq[-2]
            last_move = self.card_play_action_seq[-3]
            rival_move_type = md.get_move_type(rival_move)
            landlord_up_last_move_type = md.get_move_type(landlord_up_last_move)
            last_move_type = md.get_move_type(last_move)
            # 如果农民下家可以压过地主，则pass
            legal_actions = self.get_legal_card_play_actions(True,'landlord_up',rival_move)
            legal_lenth = len(legal_actions[0])
            # landlord__most_wanted_card_action =self.most_wanted_card['landlord'][:]
            if  legal_lenth != 0 :
                # 地主pass，up未pass，则pass
                if rival_move_type['type'] == md.PASS & landlord_up_last_move_type['type'] != md.PASS:
                    action = []
                    self.log(action)
                # down可出牌种类数大于1且牌权在up手里，则pass（可能把up堵死，但如果不这样的话当up不强势容易把地主牌权放走,需要取舍或做进一步处理）
                # 疑似潜在问题：legal_actions = [[]],长度为1。 故当出现legal_actions:[[17], []]时，有可能触发递牌
                elif len(legal_actions) > 1 & last_move_type['type'] == md.PASS & rival_move_type['type'] == md.PASS:
                    action = []
                    self.log(action)
                else:
                    actions = self.get_most_wanted_card_action()
                    if len(actions) > 0:
                        action = actions[0]
                        self.log(action)
        if len(action) > 0:
            self.last_pid = self.acting_player_position

        if action in bombs:
            self.bomb_num += 1

        self.last_move_dict[
            self.acting_player_position] = action.copy()

        self.card_play_action_seq.append(action)
        self.update_acting_player_hand_cards(action)

        self.played_cards[self.acting_player_position] += action

        if self.acting_player_position == 'landlord' and \
                len(action) > 0 and \
                len(self.three_landlord_cards) > 0:
            for card in action:
                if len(self.three_landlord_cards) > 0:
                    if card in self.three_landlord_cards:
                        self.three_landlord_cards.remove(card)
                else:
                    break

        self.game_done()
        if not self.game_over:
            self.get_most_wanted_card()
            self.get_acting_player_position()
            self.game_infoset = self.get_infoset()
    
    def log(self,action):
        # 生成log文件夹
        self.setp_flag = True
        if not os.path.exists('log'):
            os.makedirs('log')
        log_path = 'log_'+str(os.getpid())+'.txt'
        log_path = os.path.join('log',log_path)
        with open(log_path,'a') as f:
            #当前玩家角色
            f.write(f"acting_player_position:{self.acting_player_position}\n")
            #当前地主手牌
            f.write(f"landlord:{json.dumps(self.info_sets['landlord'].player_hand_cards)}\n")
            #当前地主上家手牌
            f.write(f"landlord_up:{json.dumps(self.info_sets['landlord_up'].player_hand_cards)}\n")
            #当前地主下家手牌
            f.write(f"landlord_down:{json.dumps(self.info_sets['landlord_down'].player_hand_cards)}\n")
            #当前角色可以出的所有牌型
            f.write(f"legal_actions:{json.dumps(self.game_infoset.legal_actions)}\n")
            #上两次出牌
            # f.write(f"last_two_moves:{json.dumps(self.info_sets['landlord'].last_two_moves)}\n")
            #地主上家最想要的牌型
            f.write(f"landlord_up_most_wanted_card:{json.dumps(self.most_wanted_card['landlord_up'])}\n")
            #地主下家最想要的牌型
            f.write(f"landlord_down_most_wanted_card:{json.dumps(self.most_wanted_card['landlord_down'])}\n")
            #地主上次出牌
            # f.write(f"landlord_last_move:{json.dumps(self.last_move_dict['landlord'])}\n")
            # 上次出牌
            f.write(f"last_move_dict:{json.dumps(self.last_move_dict)}\n")
            #这次所打牌型
            f.write(f"action:{json.dumps(action)}\n")
            f.write('------------------\n')

    def get_last_move(self):
        last_move = []
        if len(self.card_play_action_seq) != 0:
            if len(self.card_play_action_seq[-1]) == 0:
                last_move = self.card_play_action_seq[-2]
            else:
                last_move = self.card_play_action_seq[-1]

        return last_move

    def get_last_two_moves(self):
        last_two_moves = [[], []]
        for card in self.card_play_action_seq[-2:]:
            last_two_moves.insert(0, card)
            last_two_moves = last_two_moves[:2]
        return last_two_moves

    def get_acting_player_position(self):
        if self.acting_player_position is None:
            self.acting_player_position = 'landlord'

        else:
            if self.acting_player_position == 'landlord':
                self.acting_player_position = 'landlord_down'

            elif self.acting_player_position == 'landlord_down':
                self.acting_player_position = 'landlord_up'

            else:
                self.acting_player_position = 'landlord'

        return self.acting_player_position

    def update_acting_player_hand_cards(self, action):
        if action != []:
            for card in action:
                self.info_sets[
                    self.acting_player_position].player_hand_cards.remove(card)
            self.info_sets[self.acting_player_position].player_hand_cards.sort()
    
    def get_most_wanted_card(self):
        # 获取当前玩家的手牌
        temp_hand_cards = self.info_sets[self.acting_player_position].player_hand_cards[:]
        most_wanted_card = []
        # 如果手牌数量大于阈值，不触发
        if len(temp_hand_cards) > self.trigger_threshold:
            return
        count = 0 # 最多三次打完的牌型
        while count < 3:
            if len(temp_hand_cards) == 0:
                self.most_wanted_card[self.acting_player_position] = most_wanted_card[:]
                break
            temp_mg = MovesGener(temp_hand_cards)
            moves = temp_mg.gen_moves()
            # 选择数量最多的牌型
            most_wanted_card.append(moves[-1])
            count += 1
            # 去除已经打完的牌
            for card in moves[-1]:
                temp_hand_cards.remove(card)
            temp_hand_cards.sort()
            
    def get_legal_card_play_actions(self,flag=False,player_position=None,rival_move=None):
        action_sequence = self.card_play_action_seq
        rival_move = []
        if len(action_sequence) != 0:
            if len(action_sequence[-1]) == 0:
                rival_move = action_sequence[-2]
            else:
                rival_move = action_sequence[-1]
        position = self.acting_player_position
        if flag:
            rival_move = rival_move
            position = player_position
        mg = MovesGener(
            self.info_sets[position].player_hand_cards)
        rival_type = md.get_move_type(rival_move)
        rival_move_type = rival_type['type']
        rival_move_len = rival_type.get('len', 1)
        moves = list()

        if rival_move_type == md.TYPE_0_PASS:
            moves = mg.gen_moves()

        elif rival_move_type == md.TYPE_1_SINGLE:
            all_moves = mg.gen_type_1_single()
            moves = ms.filter_type_1_single(all_moves, rival_move)

        elif rival_move_type == md.TYPE_2_PAIR:
            all_moves = mg.gen_type_2_pair()
            moves = ms.filter_type_2_pair(all_moves, rival_move)

        elif rival_move_type == md.TYPE_3_TRIPLE:
            all_moves = mg.gen_type_3_triple()
            moves = ms.filter_type_3_triple(all_moves, rival_move)

        elif rival_move_type == md.TYPE_4_BOMB:
            all_moves = mg.gen_type_4_bomb() + mg.gen_type_5_king_bomb()
            moves = ms.filter_type_4_bomb(all_moves, rival_move)

        elif rival_move_type == md.TYPE_5_KING_BOMB:
            moves = []

        elif rival_move_type == md.TYPE_6_3_1:
            all_moves = mg.gen_type_6_3_1()
            moves = ms.filter_type_6_3_1(all_moves, rival_move)

        elif rival_move_type == md.TYPE_7_3_2:
            all_moves = mg.gen_type_7_3_2()
            moves = ms.filter_type_7_3_2(all_moves, rival_move)

        elif rival_move_type == md.TYPE_8_SERIAL_SINGLE:
            all_moves = mg.gen_type_8_serial_single(repeat_num=rival_move_len)
            moves = ms.filter_type_8_serial_single(all_moves, rival_move)

        elif rival_move_type == md.TYPE_9_SERIAL_PAIR:
            all_moves = mg.gen_type_9_serial_pair(repeat_num=rival_move_len)
            moves = ms.filter_type_9_serial_pair(all_moves, rival_move)

        elif rival_move_type == md.TYPE_10_SERIAL_TRIPLE:
            all_moves = mg.gen_type_10_serial_triple(repeat_num=rival_move_len)
            moves = ms.filter_type_10_serial_triple(all_moves, rival_move)

        elif rival_move_type == md.TYPE_11_SERIAL_3_1:
            all_moves = mg.gen_type_11_serial_3_1(repeat_num=rival_move_len)
            moves = ms.filter_type_11_serial_3_1(all_moves, rival_move)

        elif rival_move_type == md.TYPE_12_SERIAL_3_2:
            all_moves = mg.gen_type_12_serial_3_2(repeat_num=rival_move_len)
            moves = ms.filter_type_12_serial_3_2(all_moves, rival_move)

        elif rival_move_type == md.TYPE_13_4_2:
            all_moves = mg.gen_type_13_4_2()
            moves = ms.filter_type_13_4_2(all_moves, rival_move)

        elif rival_move_type == md.TYPE_14_4_22:
            all_moves = mg.gen_type_14_4_22()
            moves = ms.filter_type_14_4_22(all_moves, rival_move)

        if rival_move_type not in [md.TYPE_0_PASS,
                                   md.TYPE_4_BOMB, md.TYPE_5_KING_BOMB]:
            moves = moves + mg.gen_type_4_bomb() + mg.gen_type_5_king_bomb()

        if len(rival_move) != 0:  # rival_move is not 'pass'
            moves = moves + [[]]

        for m in moves:
            m.sort()
        return moves

    def reset(self):
        self.card_play_action_seq = []

        self.three_landlord_cards = None
        self.game_over = False

        self.acting_player_position = None
        self.player_utility_dict = None

        self.setp_flag = False

        self.last_move_dict =  {'landlord_down': [],
                               'landlord_up': [],
                               'landlord': []}

        self.played_cards = {'landlord': [],
                             'landlord_up': [],
                             'landlord_down': []}
        
        self.player_origin_cards = {'landlord': [],
                                    'landlord_up': [],
                                    'landlord_down': []}

        self.last_move = []
        self.last_two_moves = []

        self.info_sets = {'landlord': InfoSet('landlord'),
                         'landlord_up': InfoSet('landlord_up'),
                         'landlord_down': InfoSet('landlord_down')}

        self.bomb_num = 0
        self.last_pid = 'landlord'
        self.most_wanted_card = {
            'landlord': [],
            'landlord_up': [],
            'landlord_down': []
        }

    def get_infoset(self):
        self.info_sets[
            self.acting_player_position].last_pid = self.last_pid

        self.info_sets[
            self.acting_player_position].legal_actions = \
            self.get_legal_card_play_actions()

        self.info_sets[
            self.acting_player_position].bomb_num = self.bomb_num

        self.info_sets[
            self.acting_player_position].last_move = self.get_last_move()

        self.info_sets[
            self.acting_player_position].last_two_moves = self.get_last_two_moves()

        self.info_sets[
            self.acting_player_position].last_move_dict = self.last_move_dict

        self.info_sets[self.acting_player_position].num_cards_left_dict = \
            {pos: len(self.info_sets[pos].player_hand_cards)
             for pos in ['landlord', 'landlord_up', 'landlord_down']}

        self.info_sets[self.acting_player_position].other_hand_cards = []
        for pos in ['landlord', 'landlord_up', 'landlord_down']:
            if pos != self.acting_player_position:
                self.info_sets[
                    self.acting_player_position].other_hand_cards += \
                    self.info_sets[pos].player_hand_cards

        self.info_sets[self.acting_player_position].played_cards = \
            self.played_cards
        self.info_sets[self.acting_player_position].three_landlord_cards = \
            self.three_landlord_cards
        self.info_sets[self.acting_player_position].card_play_action_seq = \
            self.card_play_action_seq

        self.info_sets[
            self.acting_player_position].all_handcards = \
            {pos: self.info_sets[pos].player_hand_cards
             for pos in ['landlord', 'landlord_up', 'landlord_down']}

        return deepcopy(self.info_sets[self.acting_player_position])

class InfoSet(object):
    """
    The game state is described as infoset, which
    includes all the information in the current situation,
    such as the hand cards of the three players, the
    historical moves, etc.
    """
    def __init__(self, player_position):
        # The player position, i.e., landlord, landlord_down, or landlord_up
        self.player_position = player_position
        # The hand cands of the current player. A list.
        self.player_hand_cards = None
        # The number of cards left for each player. It is a dict with str-->int 
        self.num_cards_left_dict = None
        # The three landload cards. A list.
        self.three_landlord_cards = None
        # The historical moves. It is a list of list
        self.card_play_action_seq = None
        # The union of the hand cards of the other two players for the current player 
        self.other_hand_cards = None
        # The legal actions for the current move. It is a list of list
        self.legal_actions = None
        # The most recent valid move
        self.last_move = None
        # The most recent two moves
        self.last_two_moves = None
        # The last moves for all the postions
        self.last_move_dict = None
        # The played cands so far. It is a list.
        self.played_cards = None
        # The hand cards of all the players. It is a dict. 
        self.all_handcards = None
        # Last player position that plays a valid move, i.e., not `pass`
        self.last_pid = None
        # The number of bombs played so far
        self.bomb_num = None
