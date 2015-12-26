"""Templates and functions for html."""


section_form = """\
<form method="post" accept-charset="ASCII" autocomplete="off">
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
<form method="post" accept-charset="ASCII" style="margin-bottom:12px;"\
      autocomplete="off">
  <input type="hidden" name="hidden_name" value="{name}">
  <input type="text" name="histo_name" placeholder="new_histo_name" \
         required=true value="{name}" {disabled}>
  <input type="text" name="title" placeholder="histo-title; x-title; y-title" \
         value="{title}">
  <input type="number" name="nbins" placeholder="bins" style="width:40px;" \
         value="{bins}" min="1">
  <input type="number" name="x_low" placeholder="low" style="width:40px;" \
         step="0.01" required=true value="{low}">
  <input type="number" name="x_high" placeholder="high" style="width:40px;" \
         step="0.01" required=true value="{high}">
  <input type="submit" value="{button}">
</form>
"""


selection_form = """\
<form method="post">
  <input type="hidden" name="cut_histo_name" value="{name}">
  <input type="number" name="cut_low" placeholder="low" style="width:40px;" \
         step="0.01" value="{low}">
  <input type="number" name="cut_high" placeholder="high" style="width:40px;" \
         step="0.01" value="{high}">
  <input type="checkbox" name="nm1" {checked}> N-1
  <input type="submit" value="select events">
</form>
"""


histo_form_args = {
    'name': '', 'title': '', 'bins': '', 'low': '', 'high': '',
    'disabled': '', 'button': 'create new'
}




def add_section_create_form(cont):
    placeholder = '<!-- SECTION CREATE FORM -->'
    form = section_form.format(button='create new')
    return cont.replace(placeholder, form)


def add_section_manipulate_forms(cont, path):
    placeholder = '<!-- SECTION UPDATE FORM -->'
    form = delete_form.format(
        action_dir='../', value='delete section', name=path.split('/')[0])
    form += section_form.format(button='duplicate section')
    return cont.replace(placeholder, form)


def add_histo_create_form(cont):
    placeholder = '<!-- HISTO CREATE FORM -->'
    placeholder2 = '<!-- NO IMAGES -->'
    form = histo_form.format(**histo_form_args)
    if placeholder2 in cont:
        form = '<h2>Figures</h2>\ncreate new:<br />\n' + form
        return cont.replace(placeholder2, form)
    else:
        return cont.replace(placeholder, form)


def add_histo_manipulate_forms(cont):
    sep = '<!-- IMAGE:'
    cont_parts = cont.split(sep)

    def handle_histo_div(cont_part):
        if '<div class="img">' not in cont_part:
            return cont_part

        name = cont_part[:cont_part.find(':')]
        div_name = 'opt_' + name
        form_args = histo_form_args.copy()  # TODO get more histo info
        form_args.update({
            'name': name,
            'disabled': 'disabled',
            'button': 'update',
        })
        sel_form = selection_form.format(
            low='', high='', name=name, checked='')
        toggle = '\n'.join((
            '<a href="javascript:ToggleDiv(\'%s\')">(toggle options)</a>'
            % div_name,
        ))
        div = '\n'.join((
            '<div id="%s" style="display:none;">' % div_name,
            histo_form.format(**form_args),
            '</div>',
        ))
        cont_part = cont_part.replace('<!-- TOGGLES -->', toggle)
        cont_part = cont_part.replace('<!-- TOGGLE_DIVS -->', div)
        cont_part = cont_part.replace('<!-- SELECTION FORM -->', sel_form)
        return cont_part

    return sep.join(handle_histo_div(cp) for cp in cont_parts)
