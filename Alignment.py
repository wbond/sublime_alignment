import sublime
import sublime_plugin
import re

class AlignmentCommand(sublime_plugin.TextCommand):
    def run(self, edit):
        view = self.view
        sel = view.sel()
        max_col = 0

        settings = view.settings()

        # This handles aligning single multi-line selections
        if len(sel) == 1:
            tab_size = int(settings.get('tab_size', 8))
            use_spaces = settings.get('translate_tabs_to_spaces')
            points = []
            line_nums = [view.rowcol(line.a)[0] for line in view.lines(sel[0])]

            trim_trailing_white_space = \
                settings.get('trim_trailing_white_space_on_save')

            if settings.get('align_indent'):
                # Align the left edges by first finding the left edge
                for row in line_nums:
                    pt = view.text_point(row, 0)

                    # Skip blank lines when the user times trailing whitespace
                    line = view.line(pt)
                    if trim_trailing_white_space and line.a == line.b:
                        continue

                    char = view.substr(pt)
                    while char == ' ' or char == '\t':
                        # Turn tabs into spaces when the preference is spaces
                        if use_spaces and char == '\t':
                            view.replace(edit, sublime.Region(pt, pt+1), ' ' *
                                tab_size)

                        # Turn spaces into tabs when tabs are the preference
                        if not use_spaces and char == ' ':
                            max_pt = pt + tab_size
                            end_pt = pt
                            while view.substr(end_pt) == ' ' and end_pt < \
                                    max_pt:
                                end_pt += 1
                            view.replace(edit, sublime.Region(pt, end_pt),
                                '\t')

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
                    view.insert(edit, pt, (' ' if use_spaces else '\t') *
                        length)

                perform_mid_line = max_length == 0

            else:
                perform_mid_line = True

            alignment_chars = settings.get('alignment_chars')
            if alignment_chars == None:
                alignment_chars = []
            alignment_prefix_chars = settings.get('alignment_prefix_chars')
            if alignment_prefix_chars == None:
                alignment_prefix_chars = []
            alignment_space_chars = settings.get('alignment_space_chars')
            if alignment_space_chars == None:
                alignment_space_chars = []

            alignment_pattern = '|'.join([re.escape(ch) for ch in
                alignment_chars])

            if perform_mid_line and alignment_chars:
                points = []
                max_col = 0
                for row in line_nums:
                    pt = view.text_point(row, 0)
                    matching_region = view.find(alignment_pattern, pt)
                    if not matching_region:
                        continue
                    matching_char_pt = matching_region.a

                    insert_pt = matching_char_pt
                    # If the equal sign is part of a multi-character
                    # operator, bring the first character forward also
                    if view.substr(insert_pt-1) in alignment_prefix_chars:
                        insert_pt -= 1

                    space_pt = insert_pt
                    while view.substr(space_pt-1) == ' ':
                        space_pt -= 1

                    if view.substr(matching_char_pt) in alignment_space_chars:
                        space_pt += 1

                    # If the next equal sign is not on this line, skip the line
                    if view.rowcol(matching_char_pt)[0] != row:
                        continue

                    points.append(insert_pt)
                    max_col = max([max_col, view.rowcol(space_pt)[1]])

                # The adjustment takes care of correcting point positions
                # since spaces are being inserted, which changes the points
                adjustment = 0
                for pt in points:
                    pt += adjustment
                    length = max_col - view.rowcol(pt)[1]
                    adjustment += length
                    if length >= 0:
                        view.insert(edit, pt, ' ' * length)
                    else:
                        view.erase(edit, sublime.Region(pt + length, pt))

        # This handles aligning multiple selections
        else:
            max_col = max([view.rowcol(region.b)[1] for region in selection])

            for region in selection:
                length = max_col - view.rowcol(region.b)[1]
                view.insert(edit, region.b, ' ' * length)