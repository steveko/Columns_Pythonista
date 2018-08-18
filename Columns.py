from scene import *
import sound
import random
import math

NUM_ROWS = 18
NUM_COLUMNS = 6

BLUE = 0
GRAY = 1
GREEN = 2
PURPLE = 3
RED = 4
YELLOW = 5

NUM_COLORS = 6

TEXTURES = ['pzl:Blue3', 'pzl:Gray3', 'pzl:Green3', 'pzl:Purple3', 'pzl:Red3', 'pzl:Yellow3']

UP_DOWN = [(1, 0), (-1, 0)]
LEFT_RIGHT = [(0, -1), (0, 1)]
POS_DIAG = [(1, 1), (-1, -1)]
NEG_DIAG = [(1, -1), (-1, 1)]

LINES = [UP_DOWN, LEFT_RIGHT, POS_DIAG, NEG_DIAG]

BACKGROUND_COLOR = (.4, .4, .4)
FIELD_COLOR = (.83, 1.0, .98)

MESSAGE_BACKGROUND_COLOR = 'black'
MESSAGE_TEXT_COLOR = 'white'

INITIAL_DROP_TIME = 0.8
POINTS_UNTIL_SPEEDUP = 50
SPEEDUP_FACTOR = 0.8

class SquareNode (SpriteNode):
	
	def __init__(self, kind, coords):
		super().__init__(TEXTURES[kind])
		self.kind = kind
		self.coords = coords
		
	def set_kind(self, kind):
		save_size = self.size
		self.kind = kind
		self.texture = Texture(TEXTURES[kind])
		self.size = save_size
		
		
class GestureScene (Scene):
	
	def __init__(self):
		super().__init__()
		self.touches_dict = {}
		self.time_threshhold = 1.0
		self.max_dx_tap = 20.0
		self.max_dy_tap = 20.0
		self.min_dx_swipe = 20.0
		self.min_dy_swipe = 120.0
				
	def touch_began(self, touch):
		self.touches_dict[touch.touch_id] = (self.t, touch.location)
	
	def touch_ended(self, touch):
		(start_touch_time, start_touch_loc) = self.touches_dict[touch.touch_id]
		del self.touches_dict[touch.touch_id]
		
		# ignore long touches
		if (self.t - start_touch_time) > self.time_threshhold:
			return
		
		delta_x = touch.location.x - start_touch_loc.x
		delta_y = touch.location.y - start_touch_loc.y
		abs_dx = abs(delta_x) + 0.1
		abs_dy = abs(delta_y) + 0.1
		
		# print("dx: %f, dy: %f, dx/dy: %f, dy/dx: %f" % (delta_x, delta_y, delta_x/delta_y, delta_y/delta_x))
				
		if (abs_dx < self.max_dx_tap) and (abs_dy < self.max_dy_tap):
			self.do_tap()
		elif (abs_dx/abs_dy > 2.0) and (abs_dx > self.min_dx_swipe):
				if delta_x > 0:
					self.do_swipe_right()
				else:
					self.do_swipe_left()
		elif (abs_dy/abs_dx > 2.0) and (abs_dy > self.min_dy_swipe):
				if delta_y > 0:
					self.do_swipe_up()
				else:
					self.do_swipe_down()

	def do_tap(self):
		pass
		
	def do_swipe_right(self):
		pass
		
	def do_swipe_left(self):
		pass
				
	def do_swipe_down(self):
		pass
		
	def do_swipe_up(self):
		pass
			
			
class ColumnsGameScene (GestureScene):

	def setup(self):
		self.background_color = BACKGROUND_COLOR
		self.setup_nodes()
		self.setup_game_state()
		self.new_game()
			
	def setup_nodes(self):
		'''
		Setup all the node objects that scene uses.
		'''
		(screen_width, screen_height) = self.size
		
		# Create a single root node that all other nodes are childen of. Having a
		# single parent makes it easier to scale the game when the screen size
		# changes (e.g. when screen orientation is changed).

		self.root_node_height = screen_height
		
		# Reserve 2 "rows" for the score
		self.square_len = self.root_node_height / (NUM_ROWS+2)
		self.square_size = Size(self.square_len, self.square_len)
				
		self.root_node_width = self.square_len * NUM_COLUMNS
		
		center = self.size/2
		node_size = (self.root_node_width, self.root_node_height)
		self.root_node = SpriteNode(None, position=center, size=node_size)
		self.root_node.color = BACKGROUND_COLOR
		
		# The field node is the area where all the blocks exist. It is the
		# parent node for all of the block nodes.
		
		field_pos = (0, self.square_len)
		field_size = (self.root_node_width, self.square_len*NUM_ROWS)
		
		self.field = SpriteNode(None, position=field_pos, size=field_size)
		self.field.color = FIELD_COLOR
		self.root_node.add_child(self.field)
		
		# The scoreboard is a LabelNode that shows the score.
		
		self.scoreboard = LabelNode("Score: 0", font=('Arial Rounded MT Bold', 30.0))
		self.scoreboard.position = (0, -self.square_len*((NUM_ROWS/2)))
		self.root_node.add_child(self.scoreboard)
		
		# message_background and message_label are used to show text overlaying the
		# field. The opacity of the message_background can be set to completely
		# obscure the field (e.g. when the game is paused).
		
		self.message_background = SpriteNode(None, position=field_pos, size=field_size)
		self.message_background.color = MESSAGE_BACKGROUND_COLOR
		self.message_background.alpha = 0.8
		self.message_label = LabelNode("foo", font=('Arial Rounded MT Bold', 30.0))
		self.message_label.color = MESSAGE_TEXT_COLOR
		self.message_background.add_child(self.message_label)
		
		# Add the root node to the scene
		self.add_child(self.root_node)
		
	def setup_game_state(self):		
		# Create an array to hold the 3 squares that comprise the falling piece		
		self.falling_squares = []
		
		# Create a dict to hold the squares that have completely fallen. Keys are
		# (row, column) tuples and values are SpriteNode objects.
		self.static_squares = {}
		
		# A set of (row, column) tuples indicating which squares should be destroyed
		self.coords_to_destroy = set()
		
		# Destroy Phases:
		#
		# 0 - Nothing to destroy
		# 1 - Hide squares
		# 2 - Show squares
		# 3 - Hide squares
		# 4 - Show squares
		# 5 - Hide squares
		# 6 - Remove blocks and close resulting gaps
		self.destroy_phase = 0
		self.destroy_tick_delay = 0.15
		self.last_destroy_phase_time = 0.0
		
	def set_game_over(self):
		self.game_over = True
		self.game_over_time = self.t
		self.show_game_message("GAME OVER")
		
	def new_game(self):
		self.clear_falling_squares()
		self.clear_static_squares()
		
		self.destroy_phase = 0
		self.last_destroy_phase_time = 0.0
		self.paused = False
		self.game_over = False
		self.hide_game_message()
						
		self.fall_delay = INITIAL_DROP_TIME
		self.next_speedup_score = POINTS_UNTIL_SPEEDUP
		
		self.score = 0
		self.update_score()
		
		self.new_falling_piece()
		
	def clear_falling_squares(self):
		for square in self.falling_squares:
			square.remove_from_parent()			
		self.falling_squares = []
		
	def clear_static_squares(self):
		for coord in self.static_squares:
			square = self.static_squares[coord]
			square.remove_from_parent()
		self.static_squares = {}
		
	def update_score(self):
		self.scoreboard.text = "Score: %d" % (self.score)
		if self.score > self.next_speedup_score:
			self.fall_delay *= SPEEDUP_FACTOR
			self.next_speedup_score += POINTS_UNTIL_SPEEDUP
									
	def did_change_size(self):
		(screen_width, screen_height) = self.size
		
		# Center root node on screen
		self.root_node.position = self.size/2
		
		# Calculate root node height based on new screen dimensions
		new_root_node_height = screen_height

		# Calculate the scale factor that when multiplied with self.root_node_height
		# will result in new_root_node_height
		scale_factor = new_root_node_height / self.root_node_height
		
		# Scale the root node
		self.root_node.x_scale = scale_factor
		self.root_node.y_scale = scale_factor
		
	def new_falling_piece(self):
		self.falling_squares = []
		
		for i in range(3):
			square = self.create_square(random.randrange(NUM_COLORS), (18+i, 3))
			self.falling_squares.append(square)

		self.last_moved = self.t
		
	def position_for_coords(self, coords):
		(row, col) = coords
		x_pos = (col - (NUM_COLUMNS/2))*self.square_len + self.square_len/2.0
		y_pos = (row - (NUM_ROWS/2))*self.square_len + self.square_len/2.0
		return (x_pos, y_pos)
		
	def create_square(self, kind, coords):
		square_node = SquareNode(kind, coords)
		square_node.position = self.position_for_coords(coords)
		square_node.size = self.square_size
		self.field.add_child(square_node)
		return square_node
				
	def move_square(self, square, delta_row, delta_col):
		(row, col) = square.coords
		row += delta_row
		col += delta_col
		square.coords = (row, col)
		(x, y) = self.position_for_coords(square.coords)
		#a = Action.move_to(x, y, 0.15, TIMING_EASE_IN_OUT)
		#square.run_action(a)
		square.position = self.position_for_coords(square.coords)
		
	def falling_piece_can_drop(self):
		'''
		Return true if space below the falling piece is empty, false otherwise.
		'''
		if len(self.falling_squares) > 0:
			bottom_square = self.falling_squares[0]
			(row, col) = bottom_square.coords
			if row == 0:
				return False
			else:
				row -= 1
				coords = (row, col)
				if coords in self.static_squares:
					return False
		
		return True
		
	def coalesce_falling_piece(self):
		for square in self.falling_squares:
			coords = square.coords
			self.static_squares[coords] = square
		self.chain_reaction = 1
		self.update_coords_to_destroy(self.falling_squares)
			
	def update_coords_to_destroy(self, seed_squares):
		# starting with each square in self.falling_squares, check to see if it is
		# part of 3 or more blocks horizontally, vertically, or diagonally.
		self.coords_to_destroy = set()
		
		for square in seed_squares:
			coords = square.coords
			kind = square.kind
			for line in LINES:
				coords_in_line = self.check_for_line_at_coords(kind, coords, line)
				self.coords_to_destroy.update(coords_in_line)
		
		if len(self.coords_to_destroy) > 0:
			self.do_destroy_phase()
		else:
			# no more squares to destroy, so check for game over state
			for column in range(NUM_COLUMNS):
				if (NUM_ROWS, column) in self.static_squares:
					self.set_game_over()
		
	def check_for_line_at_coords(self, kind, coords, line):
		coords_in_line = [coords]
		length = 1
		for (delta_row, delta_col) in line:
			(row, col) = coords
			while True:
				row += delta_row
				col += delta_col
				test_coords = (row, col)
				if test_coords in self.static_squares:
					test_square = self.static_squares[test_coords]
					if test_square.kind == kind:
						length += 1
						coords_in_line.append(test_coords)
						continue
				break
		if length >= 3:
			return coords_in_line
		else:
			return []
			
	def do_destroy_phase(self):
		p = self.destroy_phase
		
		if p == 6:
			# remove squares and drop squares from above
			self.destroy_phase = 0
			self.remove_squares_at_coords(self.coords_to_destroy)
		else:			
			if p == 1 or p == 3 or p == 5:
				# hide squares at coords
				self.set_alpha(self.coords_to_destroy, 0.3)
			elif p == 2 or p == 4:
				# show squares at coords
				self.set_alpha(self.coords_to_destroy, 1.0)
				
			self.last_destroy_phase_time = self.t
			self.destroy_phase += 1
			
	def remove_squares_at_coords(self, coords):
		self.score += (len(coords) - 2)*self.chain_reaction
		self.update_score()
		
		for coord in coords:
			square = self.static_squares.pop(coord)
			square.remove_from_parent()
		
		# Close gaps in columns. Use any squares that are moved as seeds for the
		# next check for squares to destroy
		
		seed_squares = []
		
		for c in range(NUM_COLUMNS):
			column_bit_map = [(r, c) in self.static_squares for r in range(NUM_ROWS)]
			if True in column_bit_map:
				column_bit_map.reverse()
				first = column_bit_map.index(True)
				column_bit_map = column_bit_map[first:]
				column_bit_map.reverse()
				if False in column_bit_map:
					delta_row = 0
					for r in range(len(column_bit_map)):
						if column_bit_map[r] is False:
							delta_row += 1
						else:
							square = self.static_squares[(r, c)]
							self.move_square(square, -delta_row, 0)
							del self.static_squares[(r, c)]
							self.static_squares[(r-delta_row, c)] = square
							seed_squares.append(square)
							
		self.chain_reaction += 1
		self.update_coords_to_destroy(seed_squares)					
		
	def set_alpha(self, coords, alpha):
		for coord in coords:
			square = self.static_squares[coord]
			square.alpha = alpha
						
	def update(self):
		if self.paused or self.game_over:
			return
			
		if self.destroy_phase > 0:
			if self.t > (self.last_destroy_phase_time + self.destroy_tick_delay):
				self.do_destroy_phase()
		elif self.t > (self.last_moved + self.fall_delay):
			self.last_moved = self.t
			if self.falling_piece_can_drop():
				for square in self.falling_squares:
					self.move_square(square, -1, 0)
			else:
				self.coalesce_falling_piece()
				self.new_falling_piece()
	
	def do_tap(self):
		if self.game_over:
			if self.t < self.game_over_time + 3.0:
				return
			else:
				self.new_game()
				return
				
		if self.paused:
			return
			
		# rotate the falling squares
		kinds = []
		
		for square in self.falling_squares:
			kinds.append(square.kind)
		
		i = 0	
		for square in self.falling_squares:
			i = (i + 1) % 3
			square.set_kind(kinds[i])
		
	def do_swipe_right(self):
		if self.paused:
			return
		if len(self.falling_squares) > 0:
			(row, col) = self.falling_squares[0].coords
			if col < NUM_COLUMNS-1:
				if (row, col+1) not in self.static_squares:
					for square in self.falling_squares:
						self.move_square(square, 0, 1)
		
	def do_swipe_left(self):
		if self.paused:
			return
		if len(self.falling_squares) > 0:
			(row, col) = self.falling_squares[0].coords
			if col > 0:
				if (row, col-1) not in self.static_squares:
					for square in self.falling_squares:
						self.move_square(square, 0, -1)
				
	def do_swipe_down(self):
		if self.paused:
			return
		if len(self.falling_squares) > 0:
			(row, col) = self.falling_squares[0].coords
			dest_row = row
			
			while dest_row > 0:
				dest_row -= 1
				if (dest_row, col) in self.static_squares:
					dest_row += 1
					break
			
			delta_row = row - dest_row
			for square in self.falling_squares:
				self.move_square(square, -delta_row, 0)	
		
	def do_swipe_up(self):
		self.paused = not self.paused
		if self.paused:
			self.show_game_message("PAUSED", True)
		else:
			self.hide_game_message()
			
	def show_game_message(self, message, hide_board=False):
			self.message_label.text = message
			if (hide_board):
				self.message_background.alpha = 1.0
			else:
				self.message_background.alpha = 0.8
			self.root_node.add_child(self.message_background)
			
	def hide_game_message(self):
		self.message_background.remove_from_parent()
		
if __name__ == '__main__':
	run(ColumnsGameScene(), show_fps=False)
