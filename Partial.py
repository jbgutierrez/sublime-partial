import os, re, textwrap
import sublime, sublime_plugin

TEMPLATES = {
	'.css': "@import url('{0}');"  ,
	'.dust': '{> "{0}" /}'         ,
	'.erb' : "<%= render '{0}' %>" ,
	'.haml': "= render '{0}'"      ,
	'.html': "<%= render '{0}' %>" ,
	'.less': "@import '{0}';"      ,
	'.sass': "@import '{0}'"       ,
	'.scss': "@import '{0}';"      ,
	'.slim': "== render '{0}'"
}

TEMPLATES_ROOTS = [
	# 'css',
	# 'sass',
	# 'styles',
	# 'stylesheets',
	'templates',
	'views'
]

TEMPLATES_ROOTS_RE = r"^.*(\\|\/)(" + r"|".join(TEMPLATES_ROOTS) + r")(\\|\/)"

def error(value):
	sublime.error_message(value)

class PartialExtractCommand(sublime_plugin.TextCommand):
	def run(self, edit):
		self.region    = self.view.sel()[0]
		self.edit      = edit
		self.source    = self.view.file_name()
		base_name      = os.path.basename(self.source)
		self.extension = re.sub(r"^[^\.]+", '', base_name)
		partial_name   = base_name.split('.')[0] + '/'
		self.template  = TEMPLATES[self.extension]

		if self.template is None: error("Unsupported file type"); return
		if self.region.empty(): error('Please select a region'); return

		self.view.window().show_input_panel("Partial Name", partial_name, self.extract, None, None)

	def extract(self, partial_name):
		folder = os.path.dirname(self.source)

		separator = '/'

		partial_name = re.sub(r"^_{1}([^\.]+)\..*?$", '\\1', partial_name)

		if re.search(r"\/|\\", partial_name):
			tokens       = re.search(r"^(.*)(\\|\/){1}(.*?)$", partial_name)
			subfolder    = tokens.group(1)
			separator    = tokens.group(2)
			partial_name = tokens.group(3)
			folder      += separator + subfolder

			if not os.path.exists(folder): os.makedirs(folder)

		full_path = folder + separator + '_' + partial_name + self.extension

		if not os.path.exists(full_path):
			partial_code = self.view.substr(self.region).encode('utf-8')
			with open(full_path, 'w') as f: f.write(textwrap.dedent(partial_code))

			self.view.window().open_file(full_path)

			tokens = re.search(TEMPLATES_ROOTS_RE + "(.*)" + self.extension, full_path)
			if tokens: partial_name = tokens.group(4)

			replacement = self.template.format(re.sub(r"(\\|\/)_", r"\1", partial_name))
			indent = re.search(r'^(\s*)', partial_code).group(1)
			replacement = textwrap.fill(replacement, initial_indent=indent, subsequent_indent=indent)
			self.view.replace(self.edit, self.region, replacement)
			msg = partial_name + ' created successfully'
			sublime.active_window().active_view().set_status("partial_msg", msg)

		else:
			error("File exits")

class PartialDisposeCommand(sublime_plugin.TextCommand):
	def run(self, edit):
		error('Not implemented yet!')
