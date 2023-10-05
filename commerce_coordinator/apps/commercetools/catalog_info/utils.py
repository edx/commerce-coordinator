from commercetools.platform.models import LocalizedString


def ls(string_dict) -> LocalizedString:  # forced return typehint/coercion intentional to avoid bad IDE warnings
    """ Make a LocalizedString that doesn't freak out type checking, assign en to en-US as well. """
    if len(string_dict) == 1 and 'en' not in string_dict:
        # If we don't have english, this still needs to show for IT and Support in the UI
        string_dict['en'] = string_dict[string_dict.keys()[0]]

    if 'en' in string_dict:
        # Keys are CASE sensitive. String matching the pattern ^[a-z]{2}(-[A-Z]{2})?$ representing an IETF language tag
        string_dict['en-US'] = string_dict['en']

    return string_dict
