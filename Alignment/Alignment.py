import sublime
import sublime_plugin

class AlignmentCommand(sublime_plugin.TextCommand):
	@handles_not_found
	def run(self, edit):
		view = self.view
		region_set = view.sel()
		max_col    = 0
		for region in region_set:
			(row, col) = view.rowcol(region.b)
			max_col    = max([col, max_col])
		for region in region_set:
			(row, col) = view.rowcol(region.b)
			length     = max_col - col
			view.insert(edit, region.b, ' ' * length)