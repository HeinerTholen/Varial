"""Templates and functions for html."""


msg_reload = '<a href="index.html">reload</a> (automatic every 3 seconds)'

section_form = """\
<form method="post" accept-charset="ASCII" autocomplete="off">
  <input type="text" name="create section" value="new_section" required=true>
  <input type="submit" value="{button}">
</form>
"""


delete_form = """\
<form method="post" action="{action_dir}index.html" \
      onsubmit="return confirm('Really {value}?');">
  <input type="submit" name="delete" value="{value}" style="color:#f00;">
  <input type="hidden" name="{value}" value={name}>
</form>
"""


histo_form = """\
<form method="post" accept-charset="ASCII" autocomplete="off">
  <input type="hidden" name="hidden_histo_name" value="{name}">
  <input type="text" name="histo_name" placeholder="quantity" \
         required=true value="{name}" {disabled}>
  <input type="text" name="title" placeholder="histo-title; x-title; y-title" \
         value="{title}">
  <input type="number" name="bins" placeholder="bins" style="width:40px;" \
         value="{bins}" min="1">
  <input type="number" name="low" placeholder="low" style="width:40px;" \
         step="0.01" value="{low}">
  <input type="number" name="high" placeholder="high" style="width:40px;" \
         step="0.01" value="{high}">
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


def add_section_manipulate_forms(cont, section):
    placeholder = '<!-- SECTION UPDATE FORM -->'
    form = delete_form.format(
        action_dir='../', value='delete section', name=section)
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


def add_histo_manipulate_forms(cont, params, section_sel_info):
    sep = '<!-- IMAGE:'
    cont_parts = cont.split(sep)
    histos, nm1 = params['histos'], 'checked' if params['nm1'] else ''

    def handle_histo_div(cont_part):
        if '<div class="img">' not in cont_part:
            return cont_part

        name = cont_part[:cont_part.find(':')]
        histo_params = histos.get(name, ('', '', '', ''))
        div_name = 'opt_' + name
        form_args = histo_form_args.copy()
        form_args.update({
            'name': name,
            'title': histo_params[0],
            'bins': histo_params[1],
            'low': histo_params[2],
            'high': histo_params[3],
            'disabled': 'disabled',
            'button': 'update',
        })
        his_form = histo_form.format(**form_args)
        low, high = section_sel_info.get(name, ('', ''))
        sel_form = selection_form.format(
            low=low, high=high, name=name, checked=nm1)
        del_form = delete_form.format(
            value='delete histogram', name=name, action_dir='')
        toggle = '\n'.join((
            '<a href="javascript:ToggleDiv(\'%s\')">(toggle options)</a>'
            % div_name,
        ))
        div = '\n'.join((
            '<div id="%s" style="display:none;">' % div_name,
            his_form + del_form,
            '</div>',
        ))
        cont_part = cont_part.replace('<!-- TOGGLES -->', toggle)
        cont_part = cont_part.replace('<!-- TOGGLE_DIVS -->', div)
        cont_part = cont_part.replace('<!-- SELECTION FORM -->', sel_form)
        return cont_part

    return sep.join(handle_histo_div(cp) for cp in cont_parts)


def add_refresh(cont, timeout, url=''):
    tmplt = '<meta http-equiv="refresh" content="{};url={}">\n</head>'
    return cont.replace(
        '</head>',
        tmplt.format(str(int(timeout)), url)
    )
