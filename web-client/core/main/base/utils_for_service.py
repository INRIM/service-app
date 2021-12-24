# Copyright INRIM (https://www.inrim.eu)
# See LICENSE file for full licensing details.
from datetime import date, datetime, time, timedelta
from urllib.parse import quote
import logging

logger = logging.getLogger(__name__)


def data_helper_list(d, fields=[], merge_field=""):
    dres = {}
    data = d.copy()
    if not merge_field == "":
        dres = data[merge_field].copy()
        for k in fields:
            if not k == merge_field:
                dres[k] = data[k]
        return dres
    else:
        if fields:
            for k in fields:
                dres[k] = data[k]
            return dres
        else:
            return data


def list_format(list_data, fields=[], merge_field=""):
    list_res = []
    for item in list_data:
        list_res.append(data_helper_list(item, fields=fields, merge_field=merge_field))
    return list_res


class UtilsForService:

    def _finditem(self, obj, key):
        if key in obj: return obj[key]
        for k, v in obj.items():
            if isinstance(v, dict):
                item = self._finditem(v, key)
                if item is not None:
                    return item

    def deserialize_list_key_values(self, list_data):
        res = {item['name']: item['value'] for item in list_data}
        return res

    def clean_save_form_data(self, data):
        """
        Clean data dictionary
        :param data:
        :return:
        """
        dat = {}

        dat = {k.replace('_in', '').replace('_tl', '').replace('_ck', '').replace('_sel', ''): True if v == 'on' else v
               for k, v in data.items()}
        return dat

    def log_req_resp(self, req_resp: object):
        logger.info("------")
        logger.info("------")
        logger.info("--LOG RESP---")
        logger.info("..................................")
        logger.info(req_resp)
        logger.info("------")
        logger.info("------")


class RequestException(IOError):
    """There was an ambiguous exception that occurred while handling your
    request.
    """

    def __init__(self, *args, **kwargs):
        """Initialize RequestException with `request` and `response` objects."""
        response = kwargs.pop('response', None)
        self.response = response
        self.request = kwargs.pop('request', None)
        if (response is not None and not self.request and
                hasattr(response, 'request')):
            self.request = self.response.request
        super(RequestException, self).__init__(*args, **kwargs)


class InvalidURL(RequestException, ValueError):
    """The URL provided was somehow invalid."""


def unquote_unreserved(uri):
    """Un-escape any percent-escape sequences in a URI that are unreserved
    characters. This leaves all reserved, illegal and non-ASCII bytes encoded.

    :rtype: str
    """
    parts = uri.split('%')
    for i in range(1, len(parts)):
        h = parts[i][0:2]
        if len(h) == 2 and h.isalnum():
            try:
                c = chr(int(h, 16))
            except ValueError:
                raise InvalidURL("Invalid percent-escape sequence: '%s'" % h)

            if c in UNRESERVED_SET:
                parts[i] = c + parts[i][2:]
            else:
                parts[i] = '%' + parts[i]
        else:
            parts[i] = '%' + parts[i]
    return ''.join(parts)


def requote_uri(uri):
    """Re-quote the given URI.

    This function passes the given URI through an unquote/quote cycle to
    ensure that it is fully and consistently quoted.

    :rtype: str
    """
    safe_with_percent = "!#$%&'()*+,/:;=?@[]~"
    safe_without_percent = "!#$&'()*+,/:;=?@[]~"
    try:
        # Unquote only the unreserved characters
        # Then quote only illegal characters (do not quote reserved,
        # unreserved, or '%')
        return quote(unquote_unreserved(uri), safe=safe_with_percent)
    except InvalidURL:
        # We couldn't unquote the given URI, so let's try quoting it, but
        # there may be unquoted '%'s in the URI. We need to make sure they're
        # properly quoted so they do not cause issues elsewhere.
        return quote(uri, safe=safe_without_percent)
