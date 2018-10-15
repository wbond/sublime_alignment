import sublime
import sublime_plugin
import re
import math
import os
import sys

try:
    from Default.indentation import line_and_normed_pt as normed_rowcol
except ImportError:
    # This is necessary due to load order of packages in Sublime Text 2
    sys.path.append(os.path.join(sublime.packages_path(), 'Default'))
    indentation = __import__('indentation')
    reload(indentation)
    del sys.path[-1]
    normed_rowcol = indentation.line_and_normed_pt

def convert_to_mid_line_tabs(view, edit, tab_size, pt, length):
    spaces_end   = pt + length
    spaces_start = spaces_end

    while view.substr(spaces_start-1) == ' ':
        spaces_start -= 1

    spaces_len   = spaces_end - spaces_start
    normed_start = normed_rowcol(view, spaces_start)[1]
    normed_mod   = normed_start % tab_size
    tabs_len     = 0
    diff         = 0

    if normed_mod != 0:
        diff     = tab_size - normed_mod
        tabs_len += 1

    tabs_len += int(math.ceil(float(spaces_len - diff) / float(tab_size)))
    view.replace(edit, sublime.Region(spaces_start, spaces_end), '\t' * tabs_len)

    return tabs_len - spaces_len


def blank(line):
    return not line.strip()


def get_indent_level(line):
    indent_level = 0

    for c in line:
        if c == ' ' or c == '\t':
            indent_level += 1
        else:
            break

    return indent_level


def get_blocks(code):
    blocks            = []
    new_block         = []
    prev_indent_level = 0

    for i, line in enumerate(code.split('\n')):
        indent_level = get_indent_level(line)
        if not blank(line) and (indent_level == prev_indent_level):
            new_block.append(i)
        else:
            if len(new_block) > 0:
                blocks.append(new_block)
                new_block = []

            if not blank(line):
                new_block         = [i]
                prev_indent_level = indent_level

    if new_block:
        blocks.append(new_block)

    return blocks


class AlignmentCommand(sublime_plugin.TextCommand):

    def run(self, edit):
        view    = self.view
        sel     = view.sel()
        max_col = 0

        settings         = view.settings()
        tab_size         = int(settings.get('tab_size', 8))
        use_spaces       = settings.get('translate_tabs_to_spaces')
        alignment_format = settings.get('alignment_format')

        if alignment_format == None:
            alignment_format = "key-varspace-separator-value"

        def align_lines(line_nums):
            points                    = []
            max_col                   = 0
            trim_trailing_white_space = settings.get('trim_trailing_white_space_on_save')


            if settings.get('align_indent'):
                foundMax = False
                # Align the left edges by first finding the left edge
                for row in line_nums:
                    pt   = view.text_point(row, 0)
                    line = view.line(pt) # Skip blank lines when the user times trailing whitespace

                    if trim_trailing_white_space and line.a == line.b:
                        continue

                    verDef = re.search(r'(\s*(' + "|".join(settings.get('declarations')) + '))(\s+)', view.substr(line), re.I)

                    if verDef:
                        foundMax = True                      # if a declaration is present use that to align all the other rows
                        toDelete = len(verDef.group(3))      # gets the empty spaces after the declaration
                        toKeep   = pt + len(verDef.group(1)) # gets the empty space before the declaration + the declaration

                        if (toDelete > 1):
                            toDelete -= 1
                            view.erase(edit, sublime.Region(toKeep, toKeep + toDelete))

                        pt      += len(verDef.group(1)) + 1
                        max_col = max([max_col, view.rowcol(pt)[1]])
                        continue

                    char = view.substr(pt)

                    while char == ' ' or char == '\t':
                        # Turn tabs into spaces when the preference is spaces
                        if use_spaces and char == '\t':
                            view.replace(edit, sublime.Region(pt, pt + 1), ' ' * tab_size)

                        # Turn spaces into tabs when tabs are the preference
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

                    if foundMax == False:
                        max_col = max([max_col, view.rowcol(pt)[1]])

                # Adjust the left edges based on the maximum that was found
                adjustment = 0
                max_length = 0

                for pt in points:
                    pt         += adjustment
                    length     = max_col - view.rowcol(pt)[1]
                    max_length = max([max_length, length])
                    adjustment += length

                    if length > 0: # shifts text right
                        view.insert(edit, pt, (' ' if use_spaces else '\t') * length)
                    elif length < 0: # shifts text left
                        view.erase(edit, sublime.Region(pt + length, pt))

            # in both cases perform mid line alignment
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

            space_after_chars = settings.get('space_after_chars')
            if space_after_chars == None:
                space_after_chars = []

            alignment_pattern = '|'.join([re.escape(ch) for ch in alignment_chars])

            # Align text after the alignment characters
            if perform_mid_line and alignment_chars:
                points            = []
                max_col           = 0
                num_spaces_needed = 1

                # go through all lines to analyze if there are multi character operators
                for row in line_nums:
                    pt              = view.text_point(row, 0)
                    matching_region = view.find(alignment_pattern, pt)

                    if not matching_region:
                        continue

                    matching_char_pt = matching_region.a
                    insert_pt        = matching_char_pt

                    if view.substr(insert_pt - 1) in alignment_prefix_chars:
                        num_spaces_needed = 2


                for row in line_nums:
                    curr_multi_char_op = False
                    pt                 = view.text_point(row, 0)
                    matching_region    = view.find(alignment_pattern, pt)

                    if not matching_region:
                        continue

                    matching_char_pt = matching_region.a
                    end_matching_pt  = view.line(matching_char_pt).b
                    insert_pt        = matching_char_pt

                    # If the equal sign is part of a multi-character operator, bring the first character forward also
                    if view.substr(insert_pt - 1) in alignment_prefix_chars:
                        curr_multi_char_op =  True
                        insert_pt          -= 1

                    space_pt = insert_pt
                    while view.substr(space_pt - 1) in [' ', '\t']:
                        space_pt -= 1

                        # Replace tabs with spaces for consistent indenting
                        if view.substr(space_pt) == '\t':
                            view.replace(edit, sublime.Region(space_pt, space_pt + 1), ' ' * tab_size)
                            matching_char_pt += tab_size - 1
                            insert_pt        += tab_size - 1

                    if view.substr(matching_char_pt) in alignment_space_chars:
                        space_pt += 1

                    # space added after sign, if opted to
                    if view.substr(matching_char_pt) in space_after_chars:
                        char_after_op = matching_char_pt + 1

                        if not view.substr(char_after_op) in [' ']:
                            if curr_multi_char_op:
                                view.insert(edit, char_after_op, ' ' * 1)
                            else:
                                view.insert(edit, char_after_op, ' ' * num_spaces_needed)
                        else:
                            extra_spaces = re.search(r'(^\s+)', view.substr(sublime.Region(char_after_op, end_matching_pt)), re.I)
                            if extra_spaces:
                                if len(extra_spaces.group()) > num_spaces_needed:
                                    # case where it is a space, we want to truncate if there are too many
                                    view.erase(edit, sublime.Region(char_after_op, char_after_op + len(extra_spaces.group()) - num_spaces_needed))
                                elif num_spaces_needed == 2 and not curr_multi_char_op:
                                    # multi character operator (+=, *=, etc.)
                                    view.insert(edit, char_after_op, ' ')


                    # If the next equal sign is not on this line, skip the line
                    if view.rowcol(matching_char_pt)[0] != row:
                        points.append(-1)
                        continue

                    points.append(insert_pt)

                    max_col = max([max_col, normed_rowcol(view, space_pt)[1]])

                # The adjustment takes care of correcting point positions
                # since spaces are being inserted, which changes the points
                adjustment = 0
                row        = 0

                for pt in points:
                    if pt == -1:
                        continue

                    textStart  =  view.text_point(line_nums[row], 0)
                    row        += 1
                    pt         += adjustment
                    length     =  max_col - normed_rowcol(view, pt)[1]
                    adjustment += length

                    if length >= 0:
                        if alignment_format == "key-varspace-separator-value":
                            view.insert(edit, pt, ' ' * length)
                        elif alignment_format == "key-separator-varspace-value":
                            view.insert(edit, pt + 1, ' ' * length)
                        elif alignment_format == "varspace-key-separator-value":
                            view.insert(edit, textStart, ' ' * length)
                    else:
                        view.erase(edit, sublime.Region(pt + length, pt))

                    if settings.get('mid_line_tabs') and not use_spaces:
                        adjustment += convert_to_mid_line_tabs(view, edit, tab_size, pt, length)

        if len(sel) == 1:
            if settings.get('whole_file_one_line') and len(view.lines(sel[0])) == 1:
                region = sublime.Region(0, view.size())
                code   = view.substr(region)
                for line_nums in get_blocks(code):
                    align_lines(line_nums)
            else:
                points    = []
                line_nums = [view.rowcol(line.a)[0] for line in view.lines(sel[0])]
                align_lines(line_nums)

        # This handles aligning multiple selections
        else:
            # BORDAIGORL: handle multiple regions by independently aligning the n-th cursor of each line
            # Example (| is cursor position):
            #    a|bbb|cc
            #    AA|B|C
            # turns into
            #    a |bbb|c
            #    AA|B  |C

            col     = {}
            curline = view.rowcol(sel[0].begin())[0]
            j       = 0

            for i in range(0,len(sel)):

                ln = view.rowcol(sel[i].begin())[0]

                if ln != curline:
                    j       = 0
                    curline = ln

                if j in col.keys():
                    col[j].append(i)
                else:
                    col[j] = [i]

                j += 1

            for j in col.keys():

                max_col = max([normed_rowcol(view, sel[i].b)[1] for i in col[j]])

                for i in col[j]:
                    region = sel[i]
                    length = max_col - normed_rowcol(view, region.begin())[1]
                    view.insert(edit, region.begin(), ' ' * length)

                if settings.get('mid_line_tabs') and not use_spaces:
                    convert_to_mid_line_tabs(view, edit, tab_size, region.begin(), length)

