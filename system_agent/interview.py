"""Shared, one-question-at-a-time OS preferences. No disk or privilege operations."""
from .profile import DESKTOPS, LAYOUTS, LOCALES, PURPOSES, validate_choices
from .choices import validate_partial

LABELS = {
    'purpose': 'What this computer is for', 'hostname': 'Computer name',
    'username': 'Your account', 'desktop': 'Desktop', 'locale': 'Language and region',
    'keyboard': 'Keyboard', 'timezone': 'Time zone', 'encrypt': 'Disk encryption',
}


def ask(field, choose, timezone, desktops=DESKTOPS):
    if field == 'purpose':
        return PURPOSES[choose('What will you mainly use this computer for?', [
            'Software development', 'Everyday browsing and documents', 'Gaming',
            'A server', 'A mixture of things']) - 1]
    if field == 'hostname':
        return input('Name for this computer [my-computer]: ').strip() or 'my-computer'
    if field == 'username':
        return input('Name for your local account [owner]: ').strip() or 'owner'
    if field == 'desktop':
        labels = [
            'No desktop — use the local text console',
            'KDE Plasma — familiar panels, menus and many settings',
            'GNOME — a simple activities-based desktop',
            'Hyprland + Quickshell — tiling windows, three small status islands and Ghostty']
        return desktops[choose('Which desktop would you like?', [labels[DESKTOPS.index(d)] for d in desktops]) - 1]
    if field == 'locale':
        return LOCALES[choose('Which system language and regional format?', [
            'English (United States)', 'English (United Kingdom)',
            'German (Germany)', 'French (France)', 'Spanish (Spain)']) - 1]
    if field == 'keyboard':
        return LAYOUTS[choose('Which keyboard layout?', ['US', 'UK', 'German', 'French', 'Spanish']) - 1]
    if field == 'timezone':
        return timezone()
    if field == 'encrypt':
        return choose('Encrypt your files? You will need the unlock passphrase after each restart.', ['Yes', 'No']) == 1
    raise ValueError('Unknown preference')


def interview(suggestions, choose, timezone, describe, desktops=DESKTOPS):
    choices = dict(validate_partial(suggestions))
    if choices.get('desktop') not in (*desktops, None):
        print('That desktop is not available in this image yet. Please choose one below.')
        choices.pop('desktop')
    for field in LABELS:
        if field not in choices:
            while True:
                value = ask(field, choose, timezone, desktops)
                try:
                    validate_partial({field: value})
                except ValueError as error:
                    print(str(error))
                    continue
                choices[field] = value
                break
    while True:
        print('\nYour chosen setup:')
        describe(choices)
        print('These preferences are not permission to erase a disk. You will review the disk separately.')
        answer = choose('Would you like to change anything?', ['Keep these choices', *LABELS.values()])
        if answer == 1:
            return validate_choices(choices)
        field = list(LABELS)[answer - 2]
        value = ask(field, choose, timezone, desktops)
        try:
            validate_partial({field: value})
            choices[field] = value
        except ValueError as error:
            print(str(error))
