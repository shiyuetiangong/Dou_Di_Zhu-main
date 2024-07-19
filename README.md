# 斗地主补丁
> v1.0
## 补丁包1:农民配合
### 1.1 背景

之前训练的模型的,两方农民之间的配合效果较差,经常会出现配合失误或者无法达到胜利条件的情况.因此,针对这个情况,进行补丁包的设计:

### 1.2 设计思路
 1. 创建**三个**代表各方当前**最想出的牌**的**全局变量**
 > 最想出的牌代表了当前出牌者只需要**一步/两步**便可以出光所有牌(胜利)的牌型和牌,本质上,是当前出牌者在下次出牌时最迫切出的牌
 2. 在进行一次牌局时,可以将牌局分成两个部分,在手牌较多时,利用AI训练选择出牌,在手牌小于策略触发的手牌数时,会启动检验和配置最想出的牌的生成和校验.如果没有能喂的牌,则使用AI训练选择出牌.
 > 策略触发的手牌数可以自定义,暂定为3-5
 4. 递牌方在出牌时，检测全局变量判断下家农民是否需要递牌，综合判断是否给下方递牌，重复上述过程
 > 暂时规定:只有农民和农民之间的配合,农民不会故意堵地主的牌

### 1.3 涉及代码
主要涉及到的是`env`文件夹下的各个`move`操作,如`move_generator`,`move_selector`等

### 1.4 设计算法
#### 1.4.1 最想出的牌
我们通过如下算法得出某个用户最想出的牌:
- 首先检验某个用户的手牌低于策略触发的手牌数量
- 利用`move_generator`中的函数,生成所有出牌的序列和可能
- 利用贪心算法优先选择**牌数**最多的出法作为最想出的牌
- 举例如下:(忽略点数大小,仅考虑牌型)
```
我们假设现在用户的手牌为 `3334`,那么用户将会有如下的出牌序列可能:
1. 3 3 3 4
2. 3 3 4 3
3. 3 4 3 3
4. 4 3 3 3
5. 33 3 4
6. 3 33 4
7. 4 33 3
...
12. 333 4
13. 4 333
14. 3334
```
在这里,由于第14中情况它的序列长度为1,按照贪心的思路,三代一能出的牌数最多,所以其实也就代表了他最想出的牌为三代一`3334`,由此,更新该用户最想出牌的牌是`3334`,下家农民在出牌时,会检查自己是否包含三代一的牌型,用以喂给该用户.

#### 1.4.2 其他问题
- 我们同样可能会遇到,在上个例子中,虽然`3334`是用户最想要的牌,但是有可能另一个农民没有这样的牌型,另一个农民有可能有另一种三不带,如`222`,那么理论上来说,`222`的出牌对于当前用户也比较好,但是刚一开始简单起见,我们暂不处理这种情况.
- 在上个例子的第1,2,3,4中情况中,由于序列长度为4,递归会比较深,因此实际上我们不会生成这种序列,而是在长度为3时就return了.
#### 1.5 测试环境
```
#环境搭建
pip install -r requirements.txt
# 也可使用本人当前环境，保存在 my_requirements.txt
# 生成数据
python generate_eval_data.py #命令行参数根据自己情况进行选择
# 测试
python evaluate.py --landlord rlcard --landlord_up baselines/douzero_ADP/landlord_up.ckpt --landlord_down baselines/douzero_ADP/landlord_down.ckpt
```
#### 1.6 测试注意问题
- evaluate.py 17行 num_workers 表示进程数量，在自动测试根据主机自主设置，在测试部分特例时，将num_workers设置为1，避免在命令行观察输出时出现错误。
- generate_eval_data.py 57行  is_random_cards表征是否随机生成初始牌型，随机初始牌型数量默认10000
- evaluate\deep_agent.py 44行，is_show_winrate是否在命令行输出胜率等信息，默认为false，人工测试请修改为True
- evaluate\simulation.py 31 step函数，不添加策略则不需要输出，添加策略进行测试，输入参数(None,True)
- 手动输入牌局，一般只有几局，输出信息显示在命令行，- 自动测试时，开启测试所设计的策略时，会将进入策略的状态信息保存在log文件夹中
```
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
f.write(f"last_two_moves:{json.dumps(self.info_sets['landlord'].last_two_moves)}\n")
#地主上家最想要的牌型
f.write(f"landlord_up_most_wanted_card:{json.dumps(self.most_wanted_card['landlord_up'])}\n")
#地主下家最想要的牌型
f.write(f"landlord_down_most_wanted_card:{json.dumps(self.most_wanted_card['landlord_down'])}\n")
#地主上次出牌
f.write(f"landlord_last_move:{json.dumps(self.last_move_dict['landlord'])}\n")
# 上次出牌
f.write(f"last_move_dict:{json.dumps(self.last_move_dict)}\n")
#这次所打牌型
f.write(f"action:{json.dumps(action)}\n")
```