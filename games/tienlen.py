import random

# --- HELPER CLASSES ---
class CardUtil:
    # Ranks: 3,4,5,6,7,8,9,10,J,Q,K,A,2
    RANKS = ['3', '4', '5', '6', '7', '8', '9', '10', 'J', 'Q', 'K', 'A', '2']
    # Suits: Bích, Chuồn (Đen) - Rô, Cơ (Đỏ)
    SUITS = {'♠': 0, '♣': 1, '♦': 2, '♥': 3}

    @staticmethod
    def get_score(card_str):
        if not card_str: return -1
        rank_str = card_str[:-1]
        suit_str = card_str[-1]
        try:
            rank_idx = CardUtil.RANKS.index(rank_str)
            return rank_idx * 4 + CardUtil.SUITS[suit_str]
        except:
            return -1

    @staticmethod
    def get_rank_idx(score):
        return score // 4

    @staticmethod
    def is_red_pig(card_str):
        # Heo cơ hoặc Heo rô
        return '2♥' in card_str or '2♦' in card_str

    @staticmethod
    def sort_hand(hand):
        return sorted(hand, key=CardUtil.get_score)

    @staticmethod
    def get_combo_type(cards):
        """
        Trả về (loại_bộ, điểm_so_sánh)
        """
        if not cards: return None, 0
        n = len(cards)
        sorted_cards = CardUtil.sort_hand(cards)
        scores = [CardUtil.get_score(c) for c in sorted_cards]
        ranks = [CardUtil.get_rank_idx(s) for s in scores]
        max_score = scores[-1]

        # 1. Rác
        if n == 1: return 'single', max_score
        # 2. Đôi
        if n == 2 and ranks[0] == ranks[1]: return 'pair', max_score
        # 3. Sám cô
        if n == 3 and ranks[0] == ranks[1] == ranks[2]: return 'triple', max_score
        # 4. Tứ quý
        if n == 4 and ranks[0] == ranks[3]: return 'quad', max_score
        # 5. Sảnh
        if n >= 3 and 12 not in ranks:
            is_straight = True
            for i in range(n - 1):
                if ranks[i+1] != ranks[i] + 1:
                    is_straight = False; break
            if is_straight: return 'straight', max_score

        # 6. Đôi thông
        if n >= 6 and n % 2 == 0:
            pairs = []
            for i in range(0, n, 2):
                if ranks[i] != ranks[i+1]: return None, 0 
                pairs.append(ranks[i])
            if 12 in pairs: return None, 0 
            is_pine = True
            for i in range(len(pairs) - 1):
                if pairs[i+1] != pairs[i] + 1:
                    is_pine = False; break
            if is_pine:
                if n == 6: return '3_pine', max_score
                if n == 8: return '4_pine', max_score

        return None, 0

    @staticmethod
    def can_beat(last_cards, new_cards):
        last_type, last_score = CardUtil.get_combo_type(last_cards)
        new_type, new_score = CardUtil.get_combo_type(new_cards)
        
        if new_type is None: return False
        last_rank_idx = CardUtil.get_rank_idx(last_score)
        
        # Heo
        last_is_pig = (last_type == 'single' and last_rank_idx == 12)
        last_is_pig_pair = (last_type == 'pair' and last_rank_idx == 12)

        # Luật Chặt
        if new_type == 'quad': # Tứ quý
            if last_is_pig or last_is_pig_pair: return True
            if last_type == '3_pine': return True
            if last_type == 'quad' and new_score > last_score: return True

        if new_type == '3_pine': # 3 Đôi thông
            if last_is_pig: return True
            if last_type == '3_pine' and new_score > last_score: return True

        if new_type == '4_pine': # 4 Đôi thông
            if last_is_pig or last_is_pig_pair: return True
            if last_type in ['3_pine', 'quad', '4_pine']: return new_score > last_score

        # Luật thường
        if last_type == new_type:
            if last_type in ['straight', '3_pine', '4_pine'] and len(last_cards) != len(new_cards):
                return False
            return new_score > last_score

        return False

# --- BOT LOGIC ---
class TienLenBot:
    def __init__(self, name):
        self.name = name
        self.hand = []
        self.is_bot = True

    def choose_move(self, last_move_data):
        last_cards = last_move_data['cards']
        sorted_hand = CardUtil.sort_hand(self.hand)

        if not last_cards:
            return [sorted_hand[0]] # Đi đầu đánh rác nhỏ nhất

        last_type, _ = CardUtil.get_combo_type(last_cards)
        
        # Logic Bot đơn giản: Đỡ Rác và Đôi
        if last_type == 'single':
            for card in sorted_hand:
                if CardUtil.can_beat(last_cards, [card]): return [card]
                    
        elif last_type == 'pair':
            ranks = {}
            for c in sorted_hand:
                r = c[:-1]
                if r not in ranks: ranks[r] = []
                ranks[r].append(c)
            pairs = [ranks[r][:2] for r in ranks if len(ranks[r]) >= 2]
            pairs.sort(key=lambda p: CardUtil.get_score(p[1]))
            for pair in pairs:
                if CardUtil.can_beat(last_cards, pair): return pair
        
        return []

# --- GAME CLASS ---
class TienLenGame:
    def __init__(self, room_id, host_sid, is_bot_mode=False, host_name="Chủ Phòng"):
        self.room_id = room_id
        self.host_sid = host_sid
        self.seats = [None] * 4
        self.state = "WAITING"
        self.turn_index = 0
        self.last_move = {'cards': [], 'sid': None} 
        
        # --- CẬP NHẬT LUẬT BỎ VÒNG ---
        # Danh sách những người đã bỏ lượt trong vòng hiện tại
        self.round_passed_sids = set() 
        
        self.is_bot_mode = is_bot_mode
        self.first_turn_ever = True

        if is_bot_mode:
            self.add_player(host_sid, host_name)
            names = ['Máy 1', 'Máy 2', 'Máy 3']
            for i in range(3):
                bot = TienLenBot(names[i])
                self.seats[i+1] = {
                    'sid': f'BOT_{i+1}', 'name': names[i], 
                    'type': 'bot', 'obj': bot, 'hand': []
                }

    def add_player(self, sid, name):
        for i in range(4):
            if self.seats[i] is None:
                self.seats[i] = {'sid': sid, 'name': name, 'type': 'human', 'hand': []}
                return True
        return False
    def reset_game(self):
        self.state = "WAITING"
        self.last_move = {'cards': [], 'sid': None}
        self.round_passed_sids = set()
        self.turn_index = 0
        self.first_turn_ever = True
        
        # Xóa bài trên tay
        for seat in self.seats:
            if seat:
                seat['hand'] = []
                if seat.get('type') == 'bot' and 'obj' in seat:
                    seat['obj'].hand = []
    def start_game(self):
        active_seats_indices = [i for i, s in enumerate(self.seats) if s]
        if len(active_seats_indices) < 2: return False

        deck = [f"{r}{s}" for s in CardUtil.SUITS for r in CardUtil.RANKS]
        random.shuffle(deck)

        lowest_card = None
        lowest_card_holder = -1

        for i in active_seats_indices:
            hand = []
            for _ in range(13):
                if deck: hand.append(deck.pop())
            
            self.seats[i]['hand'] = CardUtil.sort_hand(hand)
            if self.seats[i]['type'] == 'bot':
                self.seats[i]['obj'].hand = self.seats[i]['hand']

            if self.first_turn_ever:
                curr_min = self.seats[i]['hand'][0]
                if lowest_card is None or CardUtil.get_score(curr_min) < CardUtil.get_score(lowest_card):
                    lowest_card = curr_min
                    lowest_card_holder = i

        self.state = "PLAYING"
        self.last_move = {'cards': [], 'sid': None}
        self.round_passed_sids = set() # Reset bỏ lượt
        
        if self.first_turn_ever:
            self.turn_index = lowest_card_holder
            self.first_turn_card = lowest_card
        else:
            self.turn_index = active_seats_indices[0] 

        return True

    def get_bot_move(self, seat_index):
        p = self.seats[seat_index]
        if not p or p['type'] != 'bot': return None
        return p['obj'].choose_move(self.last_move)

    def check_chop(self, last_cards, new_cards):
        """Kiểm tra xem có phải là CHẶT HEO/HÀNG hay không để trả về loại"""
        if not last_cards: return None
        
        last_type, last_score = CardUtil.get_combo_type(last_cards)
        new_type, _ = CardUtil.get_combo_type(new_cards)
        
        last_rank = CardUtil.get_rank_idx(last_score)
        
        # Bị chặt Heo Đơn
        if last_type == 'single' and last_rank == 12: # Rank 12 là Heo
            is_red = CardUtil.is_red_pig(last_cards[0])
            return "CHOP_PIG_RED" if is_red else "CHOP_PIG_BLACK"

        # Bị chặt Đôi Heo
        if last_type == 'pair' and last_rank == 12:
            return "CHOP_PAIR_PIG"

        # Bị chặt Tứ Quý / 3 Đôi thông / 4 Đôi thông (Chặt chồng)
        if last_type in ['quad', '3_pine', '4_pine']:
            return "CHOP_OVER" # Chặt đè

        return None

    def play_cards(self, player_idx, cards):
        current_p = self.seats[self.turn_index]
        if player_idx != self.turn_index: return False, "Chưa đến lượt"
        
        # Kiểm tra nếu bị khóa vòng (Bỏ lượt)
        # TRỪ KHI: Có 4 đôi thông thì được chặt bất kỳ lúc nào (Luật nâng cao, tạm thời làm luật cơ bản trước)
        # Ở đây làm luật chặt chẽ: Đã bỏ là nghỉ đến hết vòng.
        if current_p['sid'] in self.round_passed_sids:
             # Logic 4 đôi thông chặt heo có thể thêm ở đây nếu muốn
             return False, "Bạn đã bỏ lượt vòng này!"

        for c in cards:
            if c not in current_p['hand']: return False, "Không có bài này"

        if self.first_turn_ever and self.last_move['sid'] is None:
            if self.first_turn_card not in cards:
                return False, f"Ván đầu phải đánh {self.first_turn_card}"

        if self.last_move['cards']:
            if not CardUtil.can_beat(self.last_move['cards'], cards):
                return False, "Bài không chặt được"
        else:
            if CardUtil.get_combo_type(cards)[0] is None:
                return False, "Bộ bài không hợp lệ"

        # --- XỬ LÝ CHẶT & TRẢ VỀ KẾT QUẢ ĐỂ TÍNH TIỀN ---
        chop_type = self.check_chop(self.last_move['cards'], cards)
        victim_sid = self.last_move['sid'] if chop_type else None
        
        # Đánh bài
        for c in cards: current_p['hand'].remove(c)
        if current_p['type'] == 'bot': current_p['obj'].hand = current_p['hand']

        self.last_move = {'cards': cards, 'sid': current_p['sid']}
        # Người đánh mới -> Không ai bỏ lượt với bài mới này
        # NHƯNG: Những người đã bỏ lượt TRƯỚC ĐÓ trong vòng vẫn bị khóa
        # Logic đúng: Khi đánh bài mới đè lên, danh sách bỏ lượt giữ nguyên (đang trong vòng)
        # Chỉ reset khi tất cả bỏ và người này thắng vòng.
        
        if self.first_turn_ever: self.first_turn_ever = False

        if len(current_p['hand']) == 0:
            self.state = "FINISHED"
            self.first_turn_ever = False 
            return True, "WIN"

        self.next_turn()
        
        # Trả về loại chặt để Server xử lý tiền
        return True, chop_type if chop_type else "OK"

    def pass_turn(self, player_idx):
        if player_idx != self.turn_index: return False, "Lỗi lượt"
        if self.last_move['sid'] is None: return False, "Không được bỏ lượt khi đi đầu"

        p = self.seats[player_idx]
        
        # --- LUẬT MỚI: BỎ LƯỢT LÀ KHÓA LUÔN ---
        self.round_passed_sids.add(p['sid'])
        
        self.next_turn()
        return True, "Passed"

    def next_turn(self):
        original_index = self.turn_index
        count_check = 0
        
        while True:
            self.turn_index = (self.turn_index + 1) % 4
            p = self.seats[self.turn_index]
            count_check += 1
            
            # Nếu quay lại người đánh cuối cùng (tức là 3 người kia đều đã bỏ lượt hoặc thoát)
            # -> Hết vòng -> Người đó được đánh bài mới
            if p and p['sid'] == self.last_move['sid']:
                self.last_move = {'cards': [], 'sid': None}
                self.round_passed_sids = set() # --- RESET VÒNG ---
                break 

            # Tìm người tiếp theo: Phải còn trong bàn VÀ CHƯA BỎ LƯỢT
            if p and p['sid'] not in self.round_passed_sids:
                break
            
            # Safety break
            if count_check > 10: break

