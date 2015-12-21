"""hQuery rapidH"""

section_form = """\
<form method="post" accept-charset="ASCII">
  <input type="text" name="section_name" value="new_section_name" required=true>
  <input type="submit" value="{button}">
</form>
"""


delete_form = """\
<form method="post" action="{action_dir}index.html" \
      onsubmit="return confirm('Really {value}?');">
  <input type="submit" name="delete_{name}" value="{value}" style="color:#f00;">
</form>
"""


histo_form = """\
<form method="post" accept-charset="ASCII">
  <input type="hidden" name="hidden_name" value="{name}">
  <input type="text" name="histo_name" placeholder="new_histo_name" \
         required=true value="{name}" {disabled}>
  <input type="text" name="title" placeholder="histo-title; x-title; y-title" \
         value="{title}">
  <input type="number" name="nbins" placeholder="bins" style="width:40px;" \
         value="{bins}">
  <input type="number" name="x_low" placeholder="low" style="width:40px;" \
         step="0.01" required=true value="{low}">
  <input type="number" name="x_high" placeholder="high" style="width:40px;" \
         step="0.01" required=true value="{high}">
  <input type="submit" value="{button}">
</form>
"""


selection_form = """\
<form method="post">
  <input type="number" name="cut_low" placeholder="low" style="width:40px;" \
         step="0.01" value="{low}">
  <input type="number" name="cut_high" placeholder="high" style="width:40px;" \
         step="0.01" value="{high}">
  <input type="select events" value="{button}">
</form>
"""


histo_form_args = {
    'name': '', 'title': '', 'bins': '', 'low': '', 'high': '',
    'disabled': '', 'button': 'create new'
}


class HQueryEngine(object):
    def __init__(self):
        self.messages = []

    @staticmethod
    def add_section_create_form(cont):
        placeholder = '<!-- SECTION CREATE FORM -->'
        form = section_form.format(button='create new')
        return cont.replace(placeholder, form)

    @staticmethod
    def add_section_manipulate_forms(cont, path):
        placeholder = '<!-- SECTION UPDATE FORM -->'
        form = delete_form.format(
            action_dir='../', value='delete section', name=path.split('/')[0])
        form += section_form.format(button='duplicate section')
        return cont.replace(placeholder, form)

    @staticmethod
    def add_histo_create_form(cont):
        placeholder = '<!-- HISTO CREATE FORM -->'
        placeholder2 = '<!-- NO IMAGES -->'
        form = histo_form.format(**histo_form_args)
        if placeholder2 in cont:
            form = '<h2>Figures</h2>\ncreate new:<br />\n' + form
            return cont.replace(placeholder2, form)
        else:
            return cont.replace(placeholder, form)

    @staticmethod
    def add_histo_manipulate_forms(cont):
        sep = '<!-- IMAGE:'
        cont_parts = cont.split(sep)
        begin, cont_parts = cont_parts[0], cont_parts[1:]

        def handle_histo_div(cont_part):
            name = cont_part[:cont_part.find(':') - 1]
            div_name = 'opt_' + name
            form_args = histo_form_args.copy()  # TODO get more histo info
            form_args.update({
                'name': name,
                'disabled': 'disabled',
                'button': 'update',
            })
            sel_form = selection_form.format({'low': '', 'high': ''})
            toggle = '\n'.join((
                '<a href="javascript:ToggleDiv(\'%s\')">(toggle options)</a>'
                % div_name,
            ))
            div = '\n'.join((
                '<div id="%s" style="display:none;"><pre>' % div_name,
                histo_form.format(**form_args),
                '</pre></div>',
            ))
            cont_part = cont_part.replace('<!-- TOGGLES -->', toggle)
            cont_part = cont_part.replace('<!-- TOGGLE_DIVS -->', div)
            cont_part = cont_part.replace('<!-- SELECTION FORM -->', sel_form)
            return cont_part

        return begin + sep.join(handle_histo_div(cp) for cp in cont_parts)

    def add_messages(self, cont):
        placeholder = '<!-- MESSAGE -->'
        message = '\n'.join('<pre class="msg">%s</pre>' % m
                            for m in self.messages)
        self.messages = []
        return cont.replace(placeholder, message)

    def post(self, args, kws):
        self.messages.append('POST %s %s' % (args, kws))

    def get(self, path, cont):
        cont = self.add_messages(cont)
        depth = path.count('/')
        if not depth:
            cont = self.add_section_create_form(cont)
        elif depth == 1:
            cont = self.add_section_manipulate_forms(cont, path)
            cont = self.add_histo_create_form(cont)
            cont = self.add_histo_manipulate_forms(cont)
        return cont


engine = HQueryEngine()
