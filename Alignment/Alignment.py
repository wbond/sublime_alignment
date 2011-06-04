import sublime
import sublime_plugin

class AlignmentCommand(sublime_plugin.TextCommand):
	def run(self, edit):
		view = self.view
		selection = view.sel()
		max_col = 0
		
		# This handles aligning single multi-line selections
		if len(selection) == 1:
			tab_size = int(view.settings().get('tab_size', 8))
			use_spaces = view.settings().get('translate_tabs_to_spaces')
			points = []
			line_nums = [view.rowcol(line.a)[0] for line in view.lines(selection[0])]

			# Align the left edges by first finding the left edge
			for row in line_nums:
				pt = view.text_point(row, 0)

				char = view.substr(pt)
				while char == ' ' or char == '\t':
					# Turn tabs into spaces when the preference is to use spaces
					if use_spaces and char == '\t':
						view.replace(edit, sublime.Region(pt, pt+1), ' ' * tab_size)
					
					# Turn spaces into tabs when the preference is to use tabs
					if not use_spaces and char == ' ':
						max_pt = pt + tab_size
						end_pt = pt
						while view.substr(end_pt) == ' ' and end_pt < max_pt:
							end_pt += 1
						view.replace(edit, sublime.Region(pt, end_pt), '\t')
					
					pt += 1

					# Rollback if the left edge wraps to the next line
					if view.rowcol(pt)[0] != row:
						pt -= 1
						break
					
					char = view.substr(pt)
				
				points.append(pt)
				max_col = max([max_col, view.rowcol(pt)[1]])

			# Adjust the left edges based on the maximum that was found
			adjustment = 0
			max_length = 0
			for pt in points:
				pt += adjustment
				length = max_col - view.rowcol(pt)[1]
				max_length = max([max_length, length])
				adjustment += length
				view.insert(edit, pt, (' ' if use_spaces else '\t') * length)
			
			# If the left-edges are aligned, align the equal signs
			if max_length == 0:
				points = []
				max_col = 0
				for row in line_nums:
					pt = view.text_point(row, 0)
					equal_pt = view.find('=', pt).a

					# If the next equal sign is not on this line, skip the line
					if view.rowcol(equal_pt)[0] != row:
						continue
					
					points.append(equal_pt)
					max_col = max([max_col, view.rowcol(equal_pt)[1]])
				
				# The adjustment takes care of correcting point positions
				# since spaces are being inserted, which changes the points
				adjustment = 0
				for pt in points:
					pt += adjustment
					length = max_col - view.rowcol(pt)[1]
					adjustment += length

					# If the character before the = is not a space align that
					# char also, which handles +=, etc
					if view.substr(pt-1) != ' ':
						pt -= 1

					view.insert(edit, pt, ' ' * length)

		# This handles aligning multiple selections
		else:
			max_col = max([view.rowcol(region.b)[1] for region in selection])
			
			for region in selection:
				length = max_col - view.rowcol(region.b)[1]
				view.insert(edit, region.b, ' ' * length)