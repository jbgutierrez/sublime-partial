import os, re, textwrap
import sublime, sublime_plugin

TEMPLATES = {
	'.css': "@import url('{0}');"  ,
	'.dust': '{{> "{0}" /}}'       ,
	'.erb' : "<%= render '{0}' %>" ,
	'.haml': "= render '{0}'"      ,
	'.html': "<%= render '{0}' %>" ,
	'.less': "@import '{0}';"      ,
	'.sass': "@import '{0}'"       ,
	'.scss': "@import '{0}';"      ,
	'.slim': "== render '{0}'"
}

TEMPLATES_ROOTS = [
	'templates',
	'views'
]

TEMPLATES_ROOTS_RE = r"^(.*)(\\|\/)(" + r"|".join(TEMPLATES_ROOTS) + r")(\\|\/)"
SEPARATOR = '/'

def error(msg): sublime.error_message(msg)
def log(msg): sublime.status_message(msg)

class PartialCommandCommand(sublime_plugin.TextCommand):
	def run(self, edit, cmd='extract_navigate'):
		self.region    = self.view.sel()[0]
		self.edit      = edit
		self.source    = self.view.file_name()
		base_name      = os.path.basename(self.source)
		self.extension = re.sub(r"^[^\.]+", '', base_name)
		partial_name   = base_name.split('.')[0] + '/'
		self.template  = TEMPLATES[self.extension]

		if self.template is None: error("Unsupported file type"); return

		if cmd == 'extract_navigate':
			if self.region.empty():
				self.navigate()
			else:
				self.view.window().show_input_panel("Partial Name", partial_name, self.extract, None, None)
		elif cmd == 'dispose':
			self.dispose()
		else:
			error("Partial command not implemented yet!")

	def extract(self, partial_name):
		folder = os.path.dirname(self.source)

		match = re.search(r"^(.*)(\\|\/)", partial_name)
		if match:
			subfolders = folder + SEPARATOR + match.group(1)
			if not os.path.exists(subfolders): os.makedirs(subfolders)

		full_path = os.path.normpath(folder + SEPARATOR + partial_name + self.extension)

		if os.path.exists(full_path) and not sublime.ok_cancel_dialog("File exits. Override?", "Override"): return

		partial_code = self.view.substr(self.region).encode('utf-8')
		with open(full_path, 'w') as f: f.write(textwrap.dedent(partial_code))

		window = self.view.window()
		view = window.active_view()
		window.open_file(full_path)
		window.focus_view(view)
		sel = self.view.sel()
		last_column = sublime.Region(sel[0].b)
		sel.add(last_column)

		match = re.search(TEMPLATES_ROOTS_RE + "(.*)" + self.extension, full_path)
		if match: partial_name = match.group(5)

		replacement = self.template.format(partial_name)
		replacement = re.sub(r"(\\|\/)+", '/', replacement) # normalize path separators
		replacement = re.sub(r"\/_", '/', replacement) # strip leading underscore in partial name
		indent = re.search(r'^(\s*)', partial_code).group(1)
		replacement = textwrap.fill(replacement, initial_indent=indent, subsequent_indent=indent)
		self.view.replace(self.edit, self.region, replacement)
		msg = partial_name + ' created successfully'
		log(msg)

	def __detect_partial_path(self):
		pattern = re.sub(r"\{0\}(.).*", r'PARTIALNAME\1', self.template)
		pattern = re.sub(r"\{{2}", r'{', pattern)
		pattern = re.escape(pattern)
		pattern = re.sub(r"(.*)PARTIALNAME(.*)", r'(\s*)\1(.*)\2.*', pattern)
		line = self.view.line(self.region)
		line_contents = self.view.substr(line)
		match = re.search(pattern, line_contents)

		partial_name = match.group(2)
		folder = os.path.dirname(self.source)
		folder = re.sub(TEMPLATES_ROOTS_RE + "(.*)", r"\1\2\3\4", folder)
		full_path = os.path.normpath(folder + SEPARATOR + partial_name + self.extension)

		if not os.path.exists(full_path):
			tokens = full_path.split('/')
			file_name = '_' + tokens.pop()
			tokens.append(file_name)
			full_path = '/'.join(tokens)

		if not os.path.exists(full_path):
			full_path = None

		return full_path

	def navigate(self):
		try:
			full_path = self.__detect_partial_path()
			self.view.window().open_file(full_path)
		except:
			error("Partial not found")

	def dispose(self):
		try:
			full_path = self.__detect_partial_path()
			with open(full_path) as f: partial_code_lines = f.readlines()

			line = self.view.line(self.region)
			line_contents = self.view.substr(line)
			indent = re.search(r'^(\s*)', line_contents).group(1)

			self.view.erase(self.edit, line)

			partial_code = "".join(indent + line for line in partial_code_lines)
			self.view.insert(self.edit, line.begin(), partial_code)

			if sublime.ok_cancel_dialog("Remove File?", "Delete"): os.remove(full_path)
		except:
			error("Partial not found")
