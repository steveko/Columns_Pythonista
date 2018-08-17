from scene import *
import sound
import random
import math
A = Action

NUM_ROWS = 18
NUM_COLUMNS = 6

BLUE = 0
GRAY = 1
GREEN = 2
PURPLE = 3
RED = 4
YELLOW = 5

TEXTURES = ['pzl:Blue3', 'pzl:Gray3', 'pzl:Green3', 'pzl:Purple3', 'pzl:Red3', 'pzl:Yellow3']

UP_DOWN = [(1, 0), (-1, 0)]
LEFT_RIGHT = [(0, -1), (0, 1)]
POS_DIAG = [(1, 1), (-1, -1)]
NEG_DIAG = [(1, -1), (-1, 1)]

LINES = [UP_DOWN, LEFT_RIGHT, POS_DIAG, NEG_DIAG]

BACKGROUND_COLOR = (.4, .4, .4)

class ColumnsGameScene (Scene):
	
	def setup_nodes(self):
		(screen_width, screen_height) = self.size
		
		# Create a node for the play area. This is the parent node for all of the squares.
		# Having a single parent play area node will make it easier to adjust to screen
		# orientation changes.
		
		# Play area height is the screen_height minus some margin area at the top and bottom
		self.play_area_height = screen_height
		
		# Use the play area height to determine the square side length,
		# Reserve 2 "rows" for the score
		self.square_len = self.play_area_height / (NUM_ROWS+2)
		
		# Use square side length to determine the play area width
		self.play_area_width = self.square_len * NUM_COLUMNS
		
		# Create a node for the play area, centered on the screen
		pos = self.size/2
		self.play_area = SpriteNode(None, position=pos, size=(self.play_area_width, self.play_area_height))
		self.play_area.color = BACKGROUND_COLOR
		
		grid_area_pos = (0, self.square_len)
		grid_area_size = (self.play_area_width, self.square_len*NUM_ROWS)
		
		self.grid_area = SpriteNode(None, position=grid_area_pos, size=grid_area_size)
		self.grid_area.color = (.83, 1.0, .98)
		self.play_area.add_child(self.grid_area)
		
		self.score_display = LabelNode("Score: 0", font=('Arial Rounded MT Bold', 30.0))
		self.score_display.position = (0, -self.square_len*((NUM_ROWS/2)))
		self.play_area.add_child(self.score_display)
		
		# Make Size object for future use
		self.square_size = Size(self.square_len, self.square_len)
		
		self.message_label = LabelNode("foo", font=('Arial Rounded MT Bold', 30.0))
		self.message_label.color = 'black'
		
		# Add the play area node to the scene
		self.add_child(self.play_area)
		
	def setup_game_state(self):		
		# Create an array to hold the 3 squares that comprise the falling piece		
		self.falling_squares = []
		
		# Create a dict to hold the squares that have completely fallen. Keys are
		# (row, column) tuples and values are SpriteNode objects.
		self.fallen_squares = {}
		
		# A set of (row, column) tuples indicating which squares should be destroyed
		self.coords_to_destroy = set()
		
		# Destroy Phases:
		#
		# 0 - Nothing to destroy
		# 1 - Hide squares
		# 2 - Show squares
		# 3 - Hide squares
		# 4 - Show squares
		# 5 - Explosion
		# 6 - Remove blocks and close resulting gaps
		self.destroy_phase = 0
		self.destroy_tick_delay = 0.15
		self.last_destroy_phase_time = 0.0
		
	
	def setup(self):
		self.background_color = BACKGROUND_COLOR
		
		self.setup_nodes()
		self.setup_game_state()
		
		# Create touches_dict dictionary, used for detecting swipes
		self.touches_dict = {}

		self.new_game()
		
		
	def set_game_over(self):
		self.game_over = True
		self.game_over_time = self.t
		self.show_game_message("GAME OVER")
		
	def new_game(self):
		
		for square in self.falling_squares:
			square.remove_from_parent()
			
		self.falling_squares = []
		
		for coord in self.fallen_squares:
			square = self.fallen_squares[coord]
			square.remove_from_parent()
			
		self.fallen_squares = {}
		
		self.destroy_phase = 0
		self.last_destroy_phase_time = 0.0
		self.paused = False
		self.game_over = False
		self.hide_game_message()
						
		self.fall_delay = 1.0
		self.next_speedup_score = 100
		
		self.score = 0
		self.update_score()
		
		self.new_falling_piece()
		
		
	def update_score(self):
		self.score_display.text = "Score: %d" % (self.score)
		if self.score > self.next_speedup_score:
			self.fall_delay *= 0.8
			self.next_speedup_score += 100
									
	def did_change_size(self):
		
		(screen_width, screen_height) = self.size
		
		# Recenter play area on screen
		pos = self.size/2
		self.play_area.position = pos
		
		# Calculate new play area height based on screen dimensions
		new_play_area_height = screen_height

		# Calculate scale factor that when multiplied with self.play_area_height will result
		# in new_play_area_height
		scale_factor = new_play_area_height / self.play_area_height
		
		# Scale the play area node
		self.play_area.x_scale = scale_factor
		self.play_area.y_scale = scale_factor
		
	def new_falling_piece(self):
		self.falling_squares = []
		
		for i in range(3):
			square = self.create_square(random.randrange(6), (18+i, 3))
			self.falling_squares.append(square)

		self.last_moved = self.t
		
	def position_for_coords(self, coords):
		(row, col) = coords
		x_pos = (col - (NUM_COLUMNS/2))*self.square_len + self.square_len/2.0
		y_pos = (row - (NUM_ROWS/2))*self.square_len + self.square_len/2.0
		return (x_pos, y_pos)
		
	def create_square(self, kind, coords):
		
		pos = self.position_for_coords(coords)
		
		square_node = SpriteNode(TEXTURES[kind], position=pos, size=self.square_size)	
		square_node.kind = kind
		square_node.coords = coords
		
		self.grid_area.add_child(square_node)
		
		return square_node
		
	def set_square_kind(self, square, kind):
		square.kind = kind
		square.texture = Texture(TEXTURES[kind])
		square.size = self.square_size
		
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
				if coords in self.fallen_squares:
					return False
		
		return True
		
	def coalesce_falling_piece(self):
		for square in self.falling_squares:
			coords = square.coords
			self.fallen_squares[coords] = square
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
				if (NUM_ROWS, column) in self.fallen_squares:
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
				if test_coords in self.fallen_squares:
					test_square = self.fallen_squares[test_coords]
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
		
		if self.destroy_phase == 6:
			# remove squares and drop squares from above
			self.destroy_phase = 0
			self.remove_squares_at_coords(self.coords_to_destroy)
		else:					
			if self.destroy_phase == 1 or self.destroy_phase == 3:
				# hide squares at coords
				self.set_alpha(self.coords_to_destroy, 0.3)
			elif self.destroy_phase == 2 or self.destroy_phase == 4:
				# show squares at coords
				self.set_alpha(self.coords_to_destroy, 1.0)
			elif self.destroy_phase == 5:
				# show explosions
				self.set_texture(self.coords_to_destroy, Texture('emj:Star_1'))
				
			self.last_destroy_phase_time = self.t
			self.destroy_phase += 1
			
	def remove_squares_at_coords(self, coords):
		
		self.score += (len(coords) - 2)*self.chain_reaction
		self.update_score()
		
		for coord in coords:
			square = self.fallen_squares.pop(coord)
			square.remove_from_parent()
		
		# Close gaps in columns. Use any squares that are moved as seeds for the
		# next check for squares to destroy
		
		seed_squares = []
		
		for c in range(NUM_COLUMNS):
			column_bit_map = [(r, c) in self.fallen_squares for r in range(NUM_ROWS)]
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
							square = self.fallen_squares[(r, c)]
							self.move_square(square, -delta_row, 0)
							del self.fallen_squares[(r, c)]
							self.fallen_squares[(r-delta_row, c)] = square
							seed_squares.append(square)
							
		self.chain_reaction += 1
		self.update_coords_to_destroy(seed_squares)					
		
	def set_alpha(self, coords, alpha):
		for coord in coords:
			square = self.fallen_squares[coord]
			square.alpha = alpha
			
	def set_texture(self, coords, texture):
		for coord in coords:
			square = self.fallen_squares[coord]
			square.texture = texture
			square.size = self.square_size
						
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
	
	def touch_began(self, touch):
		self.touches_dict[touch.touch_id] = (self.t, touch.location)
	
	def touch_moved(self, touch):
		pass
			
	def touch_ended(self, touch):
		(start_touch_time, start_touch_loc) = self.touches_dict[touch.touch_id]
		del self.touches_dict[touch.touch_id]
		
		TIME_THRESHHOLD = 0.5
		DISTANCE_THRESHHOLD = 20.0
		
		# ignore long touches
		if (self.t - start_touch_time) > TIME_THRESHHOLD:
			return
		
		delta_x = touch.location.x - start_touch_loc.x
		delta_y = touch.location.y - start_touch_loc.y
				
		if (abs(delta_x) < DISTANCE_THRESHHOLD) and (abs(delta_y) < DISTANCE_THRESHHOLD):
			self.do_tap()
		else:
			if abs(delta_x) > abs(delta_y):
				if delta_x > 0:
					self.do_swipe_right()
				else:
					self.do_swipe_left()
			else:
				if delta_y > 0:
					self.do_swipe_up()
				else:
					self.do_swipe_down()
					
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
			self.set_square_kind(square, kinds[i])
		
	def do_swipe_right(self):
		if self.paused:
			return
		if len(self.falling_squares) > 0:
			(row, col) = self.falling_squares[0].coords
			if col < NUM_COLUMNS-1:
				if (row, col+1) not in self.fallen_squares:
					for square in self.falling_squares:
						self.move_square(square, 0, 1)
		
	def do_swipe_left(self):
		if self.paused:
			return
		if len(self.falling_squares) > 0:
			(row, col) = self.falling_squares[0].coords
			if col > 0:
				if (row, col-1) not in self.fallen_squares:
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
				if (dest_row, col) in self.fallen_squares:
					dest_row += 1
					break
			
			delta_row = row - dest_row
			for square in self.falling_squares:
				self.move_square(square, -delta_row, 0)	
		
	def do_swipe_up(self):
		self.paused = not self.paused
		if self.paused:
			self.show_game_message("PAUSED")
		else:
			self.hide_game_message()
			
	def show_game_message(self, message):
			self.message_label.text = message
			self.play_area.add_child(self.message_label)
			
	def hide_game_message(self):
		self.message_label.remove_from_parent()
		
if __name__ == '__main__':
	run(ColumnsGameScene(), show_fps=False)
