
########################################################################################
##
## This plugin is the client for the HashDB lookup service operated buy OALABS:
##
## https://hashdb.openanalysis.net/
##
##   _   _           _    ____________ 
##  | | | |         | |   |  _  \ ___ \ 
##  | |_| | __ _ ___| |__ | | | | |_/ /
##  |  _  |/ _` / __| '_ \| | | | ___ \ 
##  | | | | (_| \__ \ | | | |/ /| |_/ /
##  \_| |_/\__,_|___/_| |_|___/ \____/ 
##
## HashDB is a community-sourced library of hashing algorithms used in malware.
## New hash algorithms can be added here: https://github.com/OALabs/hashdb
##
## Updated for IDA 7.xx and Python 3
##
## To install:
##      Copy script into plugins directory, i.e: C:\Program Files\<ida version>\plugins
##
## To run:
##      Configure Settings:
##          Edit->Plugins->HashDB
##          click `Refresh Algorithms` to pull a list of hash algorithms
##          select the hash algorithm you need from the drop-down
##          OK
##      Lookup Hash:
##          Highlight constant in IDA disassembly or psuedocode view
##          Right-click -> HashDB Lookup
##          If a hash is found it will be added to an enum controlled in the settings
##          Right-click on the constant again -> Enum -> Select new hash enum
##
########################################################################################

import sys
import idaapi
import idautils
import idc
import ida_kernwin
from ida_kernwin import Choose
import ida_enum
import ida_bytes
import ida_netnode
import requests
import json


__AUTHOR__ = '@herrcore'

PLUGIN_NAME = "HashDB"
PLUGIN_HOTKEY = 'Alt+`'
VERSION = '1.0.0'

#--------------------------------------------------------------------------
# IDA Python version madness
#--------------------------------------------------------------------------

major, minor = map(int, idaapi.get_kernel_version().split("."))
assert (major > 6),"ERROR: HashDB plugin requires IDA v7+"
assert (sys.version_info >= (3, 0)), "ERROR: HashDB plugin requires Python 3"


#--------------------------------------------------------------------------
# Global settings
#--------------------------------------------------------------------------

HASHDB_API_URL ="https://hashdb.openanalysis.net"
HASHDB_USE_XOR = False
HASHDB_XOR_VALUE = 0
HASHDB_ALGORITHM = None
ENUM_NAME = "hashdb_strings"
NETNODE_NAME = "$ hashdb"

#--------------------------------------------------------------------------
# Setup Icon
#--------------------------------------------------------------------------

HASH_ICON_DATA = b"".join([b'\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x10\x00\x00\x00\x10\x08',
                          b'\x04\x00\x00\x00\xb5\xfa7\xea\x00\x00\x00\x04gAMA\x00\x00\xb1\x8f\x0b\xfca',
                          b'\x05\x00\x00\x00 cHRM\x00\x00z&\x00\x00\x80\x84\x00\x00\xfa\x00\x00\x00\x80',
                          b'\xe8\x00\x00u0\x00\x00\xea`\x00\x00:\x98\x00\x00\x17p\x9c\xbaQ<\x00\x00\x00',
                          b'\x02bKGD\x00\xff\x87\x8f\xcc\xbf\x00\x00\x00\tpHYs\x00\x00\x0b\x13\x00\x00',
                          b'\x0b\x13\x01\x00\x9a\x9c\x18\x00\x00\x00\x07tIME\x07\xe5\t\x18\x12\x18(\xba',
                          b'\xecz-\x00\x00\x01#IDAT(\xcfm\xd1\xbdJ\x9ba\x18\xc6\xf1_\xde<\xd5d\x08\xc1',
                          b'\xb46\x967!\x1d,\x88\xd0\xa1P\xe8\x01\x14\x0c\xb8\xbbt\xa9\xa3\x07\xd0\xb9',
                          b'\xab \x1e\x83s\x87R\xa4]K\xe8".*NEpJZL\x9b\xa2V\x90\xc6\xa4\xc6\xc7%\x92\xa0',
                          b'\xfe\xd7\xeb\xe6\xe6\xfa`\x9c\x8c\x82\x04\xe4\xe4\xdd\xc3\xb4\x0fV\x95\xf0',
                          b'\xd6\x17\x0bw\x0f\xeaz\xf6<\xf4\xc0\xa6h\x05\xc3\x877,\x98\xf0\xd5\xb1g^i\xfb',
                          b'\x06\x01AY\x10\x15\xbdv\xe9\xbb\x19\x8bf4\x0c\xa4~g\x90\xfa\xa8\xeaJ\xd6c\x89',
                          b'\x8e\xbe\xa2\xa2s\x7f\xb5\xbcI\xc6\x12\x94\x04\'\xfa\xf2\x8azNen\xa4\xac\'*^8',
                          b'\xd0\xb5\xa4\xec\xbd\xe8\xb3\xa7\xaaR!\x08\xca\x12\x03\xb3j\x9a\x0e\xe5\xbc',
                          b'\xc4\x8e\xbe\xa8c@\xcd\x96\x9f\x9a\xfe\x88\xbaZZ.D\x1d?lKG1\'\x94\\:\x11M\x99t',
                          b'\xa6;r\x10\xa4*\x96\xfd\xb7\xef\xb9Y\r\xd1;\xa9\x9aT\x18U\xb4&Z\xc7\x9c#m\xf3',
                          b'\xb7+~dOO\x1d+\xa2M\x93#);\xdc\xae\xec\x97\r\xff\x94L\xf9d\xf7\xeeL\x89\xc2',
                          b'\xd0V^n\\\xb8\x06\xd6\xa1L\xe6_H\xbf\xfc\x00\x00\x00%tEXtdate:create\x00202',
                          b'1-09-24T18:24:40+00:00\xd7;f\xf5\x00\x00\x00%tEXtdate:modify\x002021-09-24T',
                          b'18:24:40+00:00\xa6f\xdeI\x00\x00\x00WzTXtRaw profile type iptc\x00\x00x\x9c',
                          b'\xe3\xf2\x0c\x08qV((\xcaO\xcb\xccI\xe5R\x00\x03#\x0b.c\x0b\x13#\x13K\x93\x14',
                          b'\x03\x13 D\x804\xc3d\x03#\xb3T \xcb\xd8\xd4\xc8\xc4\xcc\xc4\x1c\xc4\x07\xcb',
                          b'\x80H\xa0J.\x00\xea\x17\x11t\xf2B5\x95\x00\x00\x00\x00IEND\xaeB`\x82'])
HASH_ICON = ida_kernwin.load_custom_icon(data=HASH_ICON_DATA, format="png")
XOR_ICON_DATA = b"".join([b'\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x10\x00\x00\x00\x10\x08\x04',
                         b'\x00\x00\x00\xb5\xfa7\xea\x00\x00\x00\x04gAMA\x00\x00\xb1\x8f\x0b\xfca\x05\x00',
                         b'\x00\x00 cHRM\x00\x00z&\x00\x00\x80\x84\x00\x00\xfa\x00\x00\x00\x80\xe8\x00\x00',
                         b'u0\x00\x00\xea`\x00\x00:\x98\x00\x00\x17p\x9c\xbaQ<\x00\x00\x00\x02bKGD\x00\xff',
                         b'\x87\x8f\xcc\xbf\x00\x00\x00\tpHYs\x00\x00\x0b\x13\x00\x00\x0b\x13\x01\x00\x9a',
                         b'\x9c\x18\x00\x00\x00\x07tIME\x07\xe5\t\x18\x12\x0b";\xd6\xd2\xa1\x00\x00\x00\xc3',
                         b'IDAT(\xcf\xa5\xd01N\x02\x01\x14\x04\xd0\x07B01\x9a\x10b\x89%\t\x8dg\xa0\xd0f-\xb8',
                         b'\x80x\x86\x8d\r\xd9#X\xee\x05(\x94\x0b\xd0\xd0@A\xcb\t4\xdb\x98\xd8Z\x90\xacv\x82',
                         b'Z,\xac\xab1P0\xdd\xfc\xcc\x9f\xcc\x0c\xfb\xa2\xf4\x8bU\x9c \xb5\xfcOPu\xe9F\x0b',
                         b'\x89{\x13\x1f\xd9\xf9 \xff\xbd\x15\x99;\xf2.\x11\xaa\x99\xfb,\x9a_y\x12 \x16#X3',
                         b'\x94\xd7>\xd7F\xc6\xb9|l\xa4\x97\xb9g\x19\xea\xa6^=*\xe9`\xe6K\xdb\xa9\x0b\x8b',
                         b'\x8d\xc3\x16T@*\xf1\xa2\x8f\x18!\xee\x9cI\x7f2\xac\x0cu7\xb1\x10\xe8z\xb0*\xd6',
                         b'|v(\xd2\xd4\xd6p.40\xccj\xee\x1c\xea\xef\xd4\xc7x+N\xbd?\xbe\x01\xa7\xee.6\xd9',
                         b'\xf6\xa5\xd2\x00\x00\x00%tEXtdate:create\x002021-09-24T18:11:34+00:00Vz\xe6\xba',
                         b'\x00\x00\x00%tEXtdate:modify\x002021-09-24T18:11:34+00:00\'\'^\x06\x00\x00\x00',
                         b'WzTXtRaw profile type iptc\x00\x00x\x9c\xe3\xf2\x0c\x08qV((\xcaO\xcb\xccI\xe5R',
                         b'\x00\x03#\x0b.c\x0b\x13#\x13K\x93\x14\x03\x13 D\x804\xc3d\x03#\xb3T \xcb\xd8\xd4',
                         b'\xc8\xc4\xcc\xc4\x1c\xc4\x07\xcb\x80H\xa0J.\x00\xea\x17\x11t\xf2B5\x95\x00\x00',
                         b'\x00\x00IEND\xaeB`\x82'])
XOR_ICON = ida_kernwin.load_custom_icon(data=XOR_ICON_DATA, format="png")
HUNT_ICON_DATA = b"".join([b'\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x10\x00\x00\x00\x10\x08\x04',
                          b'\x00\x00\x00\xb5\xfa7\xea\x00\x00\x00\x04gAMA\x00\x00\xb1\x8f\x0b\xfca\x05\x00',
                          b'\x00\x00 cHRM\x00\x00z&\x00\x00\x80\x84\x00\x00\xfa\x00\x00\x00\x80\xe8\x00\x00u0',
                          b'\x00\x00\xea`\x00\x00:\x98\x00\x00\x17p\x9c\xbaQ<\x00\x00\x00\x02bKGD\x00\xff\x87',
                          b'\x8f\xcc\xbf\x00\x00\x00\tpHYs\x00\x00\x0b\x13\x00\x00\x0b\x13\x01\x00\x9a\x9c\x18',
                          b'\x00\x00\x00\x07tIME\x07\xe5\t\x1d\x10#"R\xd1XW\x00\x00\x01.IDAT(\xcf\x8d\xd1;K\x9b',
                          b'\x01\x18\xc5\xf1\x9fI\xa8C\xbd\xf1\x0e\xdd\xd2\xc5NJ\x07;h\xd5\xa1\xf1\x0bT\xd4M',
                          b'\x14//\x82\xad\x8b\x83\x93`\xf1\x02~\x84\x08-b\x1c\xea\xe6\xe2 \x08^\x9aAQ\x07\x87',
                          b'R\x9d:\x99Atx\x15\xab`\xbc\xd0\x0eitS\xcf\xf2\xc0\xe1\xf0\x1c\xf8\x9f\x12\x0f*Q!@',
                          b'\xe4\xdc\xdf\x07\xb3xkuz\xe7\x05\xae\xedY\xb0_\x08\x15\x02\t=\x06l\xdap\x89\x97Z4',
                          b'\xfbf\xde-\t\xd0#4\xa1J\xef\xff\x8aE\xab\xc60[\xf8\xf0\xd6W\x93\xde\xfb`\xce!^\xeb',
                          b'\x93\xb5\xed\x8b\x01\xbf\xe2\x18v\xe4T\xbbQ\xcd\xba\xa4\\I\xebw\xe0N\x8d\xb5\x98Ju~h',
                          b'\x93\xd1\xaa\xda\xb8q\xd5>\xcah\x93U\xa72&P\xeaB \xa7\xde\x8cA\x83f4\xc8\t\xfcQ*\x88yB',
                          b'\t\x91\xbc2\x91\xa4]\x9f\xa4\xf1\xd9\x8e\xa4H\xb9\xbc(.\xaf\xd6\x1b\xebBi\xaftK\xf9i',
                          b'\xc9\x88\xef\x1a\xe5,\xc7ql\xc8\x8a;\xa1UK\xb2n\x8c\xc8\xfa\xad\xcb\xb4\x93\x02\xc9PhJ',
                          b'\x95\x8e{Pg\xc6\xcc\x16A\x15Qo\xd9p\x812-\x9a\x8a\xa8\x9f9\xd6#s\xff\x03\xabm^\xab\xaf',
                          b'\xe8z\xc0\x00\x00\x00%tEXtdate:create\x002021-09-29T16:35:34+00:00\xf4Q\xb1\xe8\x00\x00',
                          b'\x00%tEXtdate:modify\x002021-09-29T16:35:34+00:00\x85\x0c\tT\x00\x00\x00WzTXtRaw prof',
                          b'ile type iptc\x00\x00x\x9c\xe3\xf2\x0c\x08qV((\xcaO\xcb\xccI\xe5R\x00\x03#\x0b.c\x0b',
                          b'\x13#\x13K\x93\x14\x03\x13 D\x804\xc3d\x03#\xb3T \xcb\xd8\xd4\xc8\xc4\xcc\xc4\x1c',
                          b'\xc4\x07\xcb\x80H\xa0J.\x00\xea\x17\x11t\xf2B5\x95\x00\x00\x00\x00IEND\xaeB`\x82'])
HUNT_ICON = ida_kernwin.load_custom_icon(data=HUNT_ICON_DATA, format="png")


#--------------------------------------------------------------------------
# Error class
#--------------------------------------------------------------------------
class HashDBError(Exception):
    pass

#--------------------------------------------------------------------------
# HashDB API 
#--------------------------------------------------------------------------

def get_algorithms(api_url='https://hashdb.openanalysis.net'):
    algorithms_url = api_url + '/hash'
    r = requests.get(algorithms_url)
    if not r.ok:
        raise HashDBError("Get algorithms API request failed, status %s" % r.status_code)
    results = r.json()
    algorithms = [a.get('algorithm') for a in results.get('algorithms',[])]
    return algorithms


def get_strings_from_hash(algorithm, hash_value, xor_value=0, api_url='https://hashdb.openanalysis.net'):
    hash_value ^= xor_value
    hash_url = api_url + '/hash/%s/%d' % (algorithm, hash_value)
    r = requests.get(hash_url)
    if not r.ok:
        raise HashDBError("Get hash API request failed, status %s" % r.status_code)
    results = r.json()
    return results


def get_module_hashes(module_name, algorithm, permutation, api_url='https://hashdb.openanalysis.net'):
    module_url = api_url + '/module/%s/%s/%s' % (module_name, algorithm, permutation)
    r = requests.get(module_url)
    if not r.ok:
        raise HashDBError("Get hash API request failed, status %s" % r.status_code)
    results = r.json()
    return results


def hunt_hash(hash_value, api_url='https://hashdb.openanalysis.net'):
    matches = []
    hash_list = [hash_value]
    module_url = api_url + '/hunt'
    r = requests.post(module_url, json={"hashes": hash_list})
    if not r.ok:
        print(module_url)
        print(hash_list)
        print(r.json())
        raise HashDBError("Get hash API request failed, status %s" % r.status_code)
    for hit in r.json().get('hits',[]):
        algo = hit.get('algorithm',None)
        if (algo != None) and (algo not in matches):
            matches.append(algo)
    return matches


#--------------------------------------------------------------------------
# Save and restore settings
#--------------------------------------------------------------------------
def load_settings():
    global HASHDB_API_URL 
    global HASHDB_USE_XOR
    global HASHDB_XOR_VALUE 
    global HASHDB_ALGORITHM
    global ENUM_NAME
    global NETNODE_NAME
    node = ida_netnode.netnode(NETNODE_NAME)
    if ida_netnode.exist(node):
        if bool(node.hashstr("HASHDB_API_URL")):
            HASHDB_API_URL = node.hashstr("HASHDB_API_URL")
        if bool(node.hashstr("HASHDB_USE_XOR")):
            if node.hashstr("HASHDB_USE_XOR").lower() == "true":
                HASHDB_USE_XOR = True
            else: 
                HASHDB_USE_XOR = False
        if bool(node.hashstr("HASHDB_XOR_VALUE")):
            HASHDB_XOR_VALUE = int(node.hashstr("HASHDB_XOR_VALUE"))
        if bool(node.hashstr("HASHDB_ALGORITHM")):
            HASHDB_ALGORITHM = node.hashstr("HASHDB_ALGORITHM")
        if bool(node.hashstr("ENUM_NAME")):
            ENUM_NAME = node.hashstr("ENUM_NAME")
        idaapi.msg("HashDB configuration loaded!\n")
    else:
        idaapi.msg("No saved HashDB configuration\n")
    return


def save_settings():
    global HASHDB_API_URL 
    global HASHDB_USE_XOR
    global HASHDB_XOR_VALUE 
    global HASHDB_ALGORITHM
    global ENUM_NAME
    global NETNODE_NAME
    node = ida_netnode.netnode()
    if node.create(NETNODE_NAME):
        if HASHDB_API_URL != None:
            node.hashset_buf("HASHDB_API_URL", str(HASHDB_API_URL))
        if HASHDB_USE_XOR != None:
            node.hashset_buf("HASHDB_USE_XOR", str(HASHDB_USE_XOR))
        if HASHDB_XOR_VALUE != None:
            node.hashset_buf("HASHDB_XOR_VALUE", str(HASHDB_XOR_VALUE))
        if HASHDB_ALGORITHM != None:
            node.hashset_buf("HASHDB_ALGORITHM", str(HASHDB_ALGORITHM))
        if ENUM_NAME != None:
            node.hashset_buf("ENUM_NAME", str(ENUM_NAME))
        idaapi.msg("HashDB settings saved\n")
    else:
        idaapi.msg("ERROR: Unable to save HashDB settings\n")
    return


#--------------------------------------------------------------------------
# Settings form
#--------------------------------------------------------------------------
class hashdb_settings_t(ida_kernwin.Form):
    """Global settings form for hashdb"""
    def __init__(self, algorithms):
        self.__n = 0
        F = ida_kernwin.Form
        F.__init__(self,
r"""BUTTON YES* Ok
BUTTON CANCEL Cancel
HashDB Settings

{FormChangeCb}
<##API URL          :{iServer}>
<##Enum Name        :{iEnum}>
<Enable XOR:{rXor}>{cXorGroup}>  |  <##:{iXor}>(hex)
<Select algorithm :{cbAlgorithm}><Refresh Algorithms:{iBtnRefresh}>

""", {      'FormChangeCb': F.FormChangeCb(self.OnFormChange),
            'iServer': F.StringInput(),
            'iEnum': F.StringInput(),
            'cXorGroup': F.ChkGroupControl(("rXor",)),
            'iXor': F.NumericInput(tp=F.FT_RAWHEX),
            'cbAlgorithm': F.DropdownListControl(
                        items=algorithms,
                        readonly=True,
                        selval=0),
            'iBtnRefresh': F.ButtonInput(self.OnBtnRefresh),
        })

    def OnBtnRefresh(self, code=0):
        api_url = self.GetControlValue(self.iServer)
        try:
            ida_kernwin.show_wait_box("HIDECANCEL\nPlease wait...")
            algorithms = get_algorithms(api_url=api_url)
        except Exception as e:
            idaapi.msg("ERROR: HashDB API request failed: %s\n" % e)
        finally:
            ida_kernwin.hide_wait_box()
        self.cbAlgorithm.set_items(algorithms)
        self.RefreshField(self.cbAlgorithm)


    def OnFormChange(self, fid):
        if fid == -1:
            # Form is initialized
            # Hide Xor input if dissabled 
            if self.GetControlValue(self.cXorGroup) == 1:
                self.EnableField(self.iXor, True)
            else:
                self.EnableField(self.iXor, False)
            self.SetFocusedField(self.cbAlgorithm)
        elif fid == self.cXorGroup.id:
            if self.GetControlValue(self.cXorGroup) == 1:
                self.EnableField(self.iXor, True)
            else:
                self.EnableField(self.iXor, False)
        elif fid == self.cbAlgorithm.id:
            sel_idx = self.GetControlValue(self.cbAlgorithm)
        else:
            pass
            #print("Unknown fid %r" % fid)
        return 1

    @staticmethod
    def show(api_url="https://hashdb.openanalysis.net",
             enum_name="hashdb_strings",
             use_xor=False,
             xor_value=0,
             algorithms=[]):
        global HASHDB_API_URL
        global HASHDB_USE_XOR
        global HASHDB_XOR_VALUE
        global HASHDB_ALGORITHM
        global ENUM_NAME
        f = hashdb_settings_t(algorithms)
        f, args = f.Compile()
        # Set default values
        f.iServer.value = api_url
        f.iEnum.value = enum_name
        if use_xor:
            f.rXor.checked = True
        else:
            f.rXor.checked = False
        f.iXor.value = xor_value
        # Show form
        ok = f.Execute()
        if ok == 1:
            if f.cbAlgorithm.value == -1:
                # No algorithm selected bail!
                idaapi.msg("HashDB: No algorithm selected!\n")
                f.Free()
                return False
            HASHDB_ALGORITHM = f.cbAlgorithm[f.cbAlgorithm.value]
            HASHDB_USE_XOR = f.rXor.checked
            HASHDB_XOR_VALUE = f.iXor.value
            HASHDB_API_URL = f.iServer.value
            ENUM_NAME = f.iEnum.value
            f.Free()
            return True
        else:
            f.Free()
            return False


#--------------------------------------------------------------------------
# Hash collision select form
#--------------------------------------------------------------------------
class match_select_t(ida_kernwin.Form):
    """Simple form to select string match during hash collision"""
    def __init__(self, collision_strings):
        self.__n = 0
        F = ida_kernwin.Form
        F.__init__(self,
r"""BUTTON YES* Ok
HashDB Hash Collision

{FormChangeCb}
More than one string matches this hash!
<Select the correct string :{cbCollisions}>

""", {      'FormChangeCb': F.FormChangeCb(self.OnFormChange),
            'cbCollisions': F.DropdownListControl(
                        items=collision_strings,
                        readonly=True,
                        selval=0),
        })


    def OnFormChange(self, fid):
        if fid == -1:
            # Form is initialized
            self.SetFocusedField(self.cbCollisions)
        elif fid == self.cbCollisions.id:
            sel_idx = self.GetControlValue(self.cbCollisions)
        else:
            pass
            #print("Unknown fid %r" % fid)
        return 1

    @staticmethod
    def show(collision_strings):
        global HASHDB_API_URL
        global HASHDB_USE_XOR
        global HASHDB_XOR_VALUE
        global HASHDB_ALGORITHM
        f = match_select_t(collision_strings)
        f, args = f.Compile()
        # Show form
        ok = f.Execute()
        if ok == 1:
            string_selection = f.cbCollisions[f.cbCollisions.value]
            f.Free()
            return string_selection
        else:
            f.Free()
            return None


#--------------------------------------------------------------------------
# Hash hunt results form
#--------------------------------------------------------------------------

class hunt_result_form_t(ida_kernwin.Form):

    class algorithm_chooser_t(ida_kernwin.Choose):
        """
        A simple chooser to be used as an embedded chooser
        """
        def __init__(self, algo_list):
            ida_kernwin.Choose.__init__(
                self,
                "",
                [
                    ["Algorithm", 30]
                ],
                flags=0,
                embedded=True,
                width=30,
                height=6)
            self.items = algo_list
            self.icon = None

        def OnGetLine(self, n):
            return self.items[n]

        def OnGetSize(self):
            return len(self.items)

    def __init__(self, algo_list, msg):
        self.invert = False
        F = ida_kernwin.Form
        F.__init__(
            self,
            r"""BUTTON YES* OK
Matched Algorithms

{FormChangeCb}
{cStrStatus}
<:{cAlgoChooser}>
""", {
            'cStrStatus': F.StringLabel(msg),
            'FormChangeCb': F.FormChangeCb(self.OnFormChange),
            'cAlgoChooser' : F.EmbeddedChooserControl(hunt_result_form_t.algorithm_chooser_t(algo_list))
        })

    def OnFormChange(self, fid):
        if fid == -1:
            # Hide algorithm chooser if empty
            if self.cAlgoChooser.chooser.items == []:
                self.ShowField(self.cAlgoChooser, False)
        return 1

    def show(algo_list):
        global HASHDB_API_URL
        global HASHDB_USE_XOR
        global HASHDB_XOR_VALUE
        global HASHDB_ALGORITHM
        # Set default values
        if len(algo_list) == 0:
            msg = "No algorithms matched the hash."
            f = hunt_result_form_t(algo_list, msg)
        else:
            msg = "The following algorithms contain a matching hash.\nSelect an algorithm to set as the default for HashDB."
            # Convert algo_list into matrix format for chooser
            algo_matrix = []
            for algo in algo_list:
                algo_matrix.append([algo])
            f = hunt_result_form_t(algo_matrix, msg)
        f, args = f.Compile()
        # Show form
        ok = f.Execute()
        if ok == 1:
            if f.cAlgoChooser.selection == None:
                # No algorithm selected bail!
                f.Free()
                return False
            HASHDB_ALGORITHM = f.cAlgoChooser.chooser.items[f.cAlgoChooser.selection[0]][0]
            f.Free()
            return True
        else:
            f.Free()
            return False


#--------------------------------------------------------------------------
# Module import select form
#--------------------------------------------------------------------------
class api_import_select_t(ida_kernwin.Form):
    """Simple form to select module to import apis from"""
    def __init__(self, string_value, module_list):
        self.__n = 0
        F = ida_kernwin.Form
        F.__init__(self,
r"""BUTTON YES* Import
BUTTON CANCEL No
HashDB Bulk Import

{FormChangeCb}
{cStr1} 
Do you want to import all function hashes from this module?
<Select module :{cbModules}>

""", {      'FormChangeCb': F.FormChangeCb(self.OnFormChange),
            'cStr1': F.StringLabel("<span style='float:left;'>The hash for <b>"+string_value+"</b> is a module function.<span>", tp=F.FT_HTML_LABEL),
            'cbModules': F.DropdownListControl(
                        items=module_list,
                        readonly=True,
                        selval=0),
        })


    def OnFormChange(self, fid):
        if fid == -1:
            # Form is initialized
            self.SetFocusedField(self.cbModules)
        elif fid == self.cbModules.id:
            sel_idx = self.GetControlValue(self.cbModules)
        else:
            pass
            #print("Unknown fid %r" % fid)
        return 1

    @staticmethod
    def show(string_value, module_list):
        f = api_import_select_t(string_value, module_list)
        f, args = f.Compile()
        # Show form
        ok = f.Execute()
        if ok == 1:
            module_selection = f.cbModules[f.cbModules.value]
            f.Free()
            return module_selection
        else:
            f.Free()
            return None


#--------------------------------------------------------------------------
# IDA helper functions
#--------------------------------------------------------------------------
def add_enums(hash_list):
    '''
    Add a list of string,hash pairs to enum.
    hash_list = [(string1,hash1),(string2,hash2)]
    '''
    global ENUM_NAME
    # Create enum
    enum_id = idc.add_enum(-1, ENUM_NAME, ida_bytes.dec_flag())
    if enum_id == idaapi.BADNODE:
        # Enum already exists attempt to find it
        enum_id = ida_enum.get_enum(ENUM_NAME)
    if enum_id == idaapi.BADNODE:
        # Can't create or find enum
        return None
    for element in hash_list:
        ida_enum.add_enum_member(enum_id, element[0], element[1])
    return enum_id


def make_const_enum(enum_id, hash_value):
    # We are in the disassembler we can set the enum directly
    ea = idc.here()
    start = idaapi.get_item_head(ea)
    # Find the operand position
    if idc.get_operand_value(ea,0) == hash_value:
        ida_bytes.op_enum(start, 0, enum_id, 0)
        return True
    elif idc.get_operand_value(ea,1) == hash_value:
        ida_bytes.op_enum(start, 1, enum_id, 0)
        return True
    else:
        return False


#--------------------------------------------------------------------------
# Global settings
#--------------------------------------------------------------------------
def global_settings():
    global HASHDB_API_URL
    global HASHDB_USE_XOR
    global HASHDB_XOR_VALUE
    global HASHDB_ALGORITHM
    global ENUM_NAME
    if HASHDB_ALGORITHM != None:
        algorithms = [HASHDB_ALGORITHM]
    else:
        algorithms = []
    settings_results = hashdb_settings_t.show(api_url=HASHDB_API_URL, 
                                                  enum_name=ENUM_NAME,
                                                  use_xor=HASHDB_USE_XOR,
                                                  xor_value=HASHDB_XOR_VALUE,
                                                  algorithms=algorithms)
    if settings_results:
        idaapi.msg("HashDB configured successfully!\nHASHDB_API_URL: %s\nHASHDB_USE_XOR: %s\nHASHDB_XOR_VALUE: %s\nHASHDB_ALGORITHM: %s\n" % 
                   (HASHDB_API_URL, HASHDB_USE_XOR, hex(HASHDB_XOR_VALUE), HASHDB_ALGORITHM))
    else:
        idaapi.msg("HashDB configuration cancelled!\n")
    return 


#--------------------------------------------------------------------------
# Set xor key
#--------------------------------------------------------------------------
def set_xor_key():
    """
    Set xor key from selection
    """
    global HASHDB_USE_XOR
    global HASHDB_XOR_VALUE
    identifier = None
    xor_value = None
    v = ida_kernwin.get_current_viewer()
    thing = ida_kernwin.get_highlight(v)
    if thing and thing[1]:
        identifier = thing[0]
    if identifier == None:
        idaapi.msg("ERROR: Not a valid xor selection\n")
        return False
    elif ('h' in identifier) or ('0x' in identifier):
        xor_value = int(identifier.replace('h',''),16)
        idaapi.msg("Hex value found %s\n" % hex(xor_value))
    else:
        xor_value = int(identifier)
        idaapi.msg("Decimal value found %s\n" % hex(xor_value))
    HASHDB_XOR_VALUE = xor_value
    HASHDB_USE_XOR = True
    idaapi.msg("XOR key set: %s\n" % hex(xor_value))
    return True
    

#--------------------------------------------------------------------------
# Hash lookup
#--------------------------------------------------------------------------
def hash_lookup():
    """
    Lookup hash from highlighted text
    """
    global HASHDB_API_URL
    global HASHDB_USE_XOR
    global HASHDB_XOR_VALUE
    global HASHDB_ALGORITHM
    global ENUM_NAME
    # If algorithm not selected pop up box to select
    # Lookup hash with algorithm 
    identifier = None
    hash_value = None
    v = ida_kernwin.get_current_viewer()
    thing = ida_kernwin.get_highlight(v)
    if thing and thing[1]:
        identifier = thing[0]
    if identifier == None:
        idaapi.msg("ERROR: Not a valid hash selection\n")
        return
    elif ('h' in identifier) or ('0x' in identifier):
        hash_value = int(identifier.replace('h',''),16)
        idaapi.msg("Hex value found %s\n" % hex(hash_value))
    else:
        hash_value = int(identifier)
        idaapi.msg("Decimal value found %s\n" % hex(hash_value))
    
    # If there is no algorithm selected pop settings window
    if HASHDB_ALGORITHM == None:
        warn_result = idaapi.warning("Please select a hash algorithm before using HashDB.")
        settings_results = hashdb_settings_t.show(api_url=HASHDB_API_URL, 
                                                  enum_name=ENUM_NAME,
                                                  use_xor=HASHDB_USE_XOR,
                                                  xor_value=HASHDB_XOR_VALUE,
                                                  algorithms=[])
        if settings_results:
            idaapi.msg("HashDB configured successfully!\nHASHDB_API_URL: %s\nHASHDB_USE_XOR: %s\nHASHDB_XOR_VALUE: %s\nHASHDB_ALGORITHM: %s\n" % 
                       (HASHDB_API_URL, HASHDB_USE_XOR, hex(HASHDB_XOR_VALUE), HASHDB_ALGORITHM))
        else:
            idaapi.msg("HashDB configuration cancelled!\n")
            return 
    # Lookup hash
    try:
        ida_kernwin.show_wait_box("HIDECANCEL\nPlease wait...")
        if HASHDB_USE_XOR:
            hash_results = get_strings_from_hash(HASHDB_ALGORITHM, hash_value, xor_value=HASHDB_XOR_VALUE, api_url=HASHDB_API_URL)
        else:
            hash_results = get_strings_from_hash(HASHDB_ALGORITHM, hash_value, api_url=HASHDB_API_URL)
    except Exception as e:
        idaapi.msg("ERROR: HashDB API request failed: %s\n" % e)
        return
    finally:
        ida_kernwin.hide_wait_box()
    hash_list = hash_results.get('hashes',[])
    if len(hash_list) == 0:
        idaapi.msg("No Hash found for %s\n" % hex(hash_value))
        return
    elif len(hash_list) == 1:
        hash_string = hash_list[0].get('string',{})
    else:
        # Multiple hashes found
        # Allow the user to select the best match
        collisions = {}
        for string_match in hash_list:
            string_value = string_match.get('string','')
            if string_value.get('is_api',False):
                collisions[string_value.get('api','')] = string_value
            else:
                collisions[string_value.get('string','')] = string_value
        selected_string = match_select_t.show(list(collisions.keys()))
        hash_string = collisions[selected_string]

    # Parse string from hash_string match
    if hash_string.get('is_api',False):
        string_value = hash_string.get('api','')
    else:
        string_value = hash_string.get('string','')

    idaapi.msg("Hash match found: %s\n" % string_value)
    # Add hash to enum
    enum_id = add_enums([(string_value,hash_value)])
    # Exit if we can't create the enum
    if enum_id == None:
        idaapi.msg("ERROR: Unable to create or find enum: %s\n" % ENUM_NAME)
        return
    # If the hash was pulled from the disassembly window
    # make the constant an enum 
    # TODO: I don't know how to do this in the decompiler window
    if ida_kernwin.get_viewer_place_type(ida_kernwin.get_current_viewer()) == ida_kernwin.TCCPT_IDAPLACE:
        make_const_enum(enum_id, hash_value)
    if hash_string.get('is_api',False):
        # If the hash is an API ask if the user wants to 
        # import all of the hashes from the module and permutation
        module_name = api_import_select_t.show(string_value, hash_string.get('modules',[]))
        if module_name != None:
            try:
                ida_kernwin.show_wait_box("HIDECANCEL\nPlease wait...")
                module_hash_list = get_module_hashes(module_name, HASHDB_ALGORITHM, hash_string.get('permutation',''), api_url=HASHDB_API_URL)
                # Parse hash and string from list into tuple list [(string,hash)]
                enum_list = []
                for function_entry in module_hash_list.get('hashes',[]):
                    # If xor is enabled we must convert the hashes
                    if HASHDB_USE_XOR:
                        enum_list.append((function_entry.get('string',{}).get('api',''),HASHDB_XOR_VALUE^function_entry.get('hash',0)))
                    else:
                        enum_list.append((function_entry.get('string',{}).get('api',''),function_entry.get('hash',0)))
                # Add hashes to enum
                enum_id = add_enums(enum_list)
                if enum_id == None:
                    idaapi.msg("ERROR: Unable to create or find enum: %s\n" % ENUM_NAME)
                else:
                    idaapi.msg("Added %d hashes for module %s\n" % (len(enum_list),module_name))
            except Exception as e:
                idaapi.msg("ERROR: HashDB build load failed: %s\n" % e)
                return
            finally:
                ida_kernwin.hide_wait_box()
    return 


#--------------------------------------------------------------------------
# Algorithm search function
#--------------------------------------------------------------------------
def hunt_algorithm():
    global HASHDB_API_URL
    global HASHDB_USE_XOR
    global HASHDB_XOR_VALUE
    # Get selected hash
    identifier = None
    hash_value = None
    v = ida_kernwin.get_current_viewer()
    thing = ida_kernwin.get_highlight(v)
    if thing and thing[1]:
        identifier = thing[0]
    if identifier == None:
        idaapi.msg("ERROR: Not a valid hash selection\n")
        return
    elif ('h' in identifier) or ('0x' in identifier):
        hash_value = int(identifier.replace('h',''),16)
        idaapi.msg("Hex value found %s\n" % hex(hash_value))
    else:
        hash_value = int(identifier)
    # If xor is set then xor hash first
    if HASHDB_USE_XOR:
        hash_value ^=HASHDB_XOR_VALUE
    # Hunt for an algorithm
    try:
        ida_kernwin.show_wait_box("HIDECANCEL\nPlease wait...")
        match_results = hunt_hash(hash_value, api_url=HASHDB_API_URL)
    except Exception as e:
        idaapi.msg("ERROR: HashDB API request failed: %s\n" % e)
        return
    finally:
        ida_kernwin.hide_wait_box()
    # Show results chooser
    # Results chooser will set algorithm
    results = hunt_result_form_t.show(match_results)


#--------------------------------------------------------------------------
# Plugin
#--------------------------------------------------------------------------
class HashDB_Plugin_t(idaapi.plugin_t):
    """
    IDA Plugin for HashDB lookup service
    """
    comment = "HashDB Lookup Service"
    help = ""
    wanted_name = PLUGIN_NAME
    # We only want a hotkey for the actual hash lookup
    wanted_hotkey = ''
    flags = idaapi.PLUGIN_KEEP

    #--------------------------------------------------------------------------
    # Plugin Overloads
    #--------------------------------------------------------------------------
    def init(self):
        """
        This is called by IDA when it is loading the plugin.
        """
        global p_initialized

        # Check if already initialized 
        if p_initialized is False:
            p_initialized = True
            ## Print a nice header
            print("=" * 80)
            print(r"   _   _           _    ____________ ")
            print(r"  | | | |         | |   |  _  \ ___ \ ")
            print(r"  | |_| | __ _ ___| |__ | | | | |_/ /")
            print(r"  |  _  |/ _` / __| '_ \| | | | ___ \ ")
            print(r"  | | | | (_| \__ \ | | | |/ /| |_/ /")
            print(r"  \_| |_/\__,_|___/_| |_|___/ \____/ ")
            print("")                 
            print("\nHashDB v{0} by @herrcore".format(VERSION))
            print("\nFindYara search shortcut key is {0}".format(PLUGIN_HOTKEY))
            print("=" * 80)
            # Load saved settings if they exist
            load_settings()
            # initialize the menu actions our plugin will inject
            self._init_action_hash_lookup()
            self._init_action_set_xor()
            self._init_action_hunt()
            # initialize plugin hooks
            self._init_hooks()
            return idaapi.PLUGIN_KEEP


    def run(self, arg):
        """
        This is called by IDA when the plugin is run from the plugins menu
        """
        global_settings()
        


    def term(self):
        """
        This is called by IDA when it is unloading the plugin.
        """
        # Save settings
        save_settings()
        # unhook our plugin hooks
        self._hooks.unhook()
        # unregister our actions & free their resources
        self._del_action_hash_lookup()
        self._del_action_set_xor()
        self._del_action_hunt()
        # done
        idaapi.msg("%s terminated...\n" % self.wanted_name)


    #--------------------------------------------------------------------------
    # IDA Actions
    #--------------------------------------------------------------------------
    ACTION_HASH_LOOKUP  = "hashdb:hash_lookup"
    ACTION_SET_XOR  = "hashdb:set_xor"
    ACTION_HUNT  = "hashdb:hunt"

    def _init_action_hash_lookup(self):
        """
        Register the hash lookup action with IDA.
        """
        action_desc = idaapi.action_desc_t( self.ACTION_HASH_LOOKUP,         # The action name.
                                            "HashDB Lookup",                     # The action text.
                                            IDACtxEntry(hash_lookup),        # The action handler.
                                            PLUGIN_HOTKEY,                  # Optional: action shortcut
                                            "Lookup hash",   # Optional: tooltip
                                            HASH_ICON
                                            )
        # register the action with IDA
        assert idaapi.register_action(action_desc), "Action registration failed"


    def _init_action_set_xor(self):
        """
        Register the set xor action with IDA.
        """
        action_desc = idaapi.action_desc_t(
            self.ACTION_SET_XOR,         # The action name.
            "HashDB set XOR key",                     # The action text.
            IDACtxEntry(set_xor_key),        # The action handler.
            None,                  # Optional: action shortcut
            "Set XOR key",   # Optional: tooltip
            XOR_ICON
        )
        # register the action with IDA
        assert idaapi.register_action(action_desc), "Action registration failed"


    def _init_action_hunt(self):
        """
        Register the hunt action with IDA.
        """
        action_desc = idaapi.action_desc_t(
            self.ACTION_HUNT,         # The action name.
            "HashDB Hunt Algorithm",                     # The action text.
            IDACtxEntry(hunt_algorithm),        # The action handler.
            None,                  # Optional: action shortcut
            "Identify algorithm based on hash",   # Optional: tooltip
            HUNT_ICON
        )
        # register the action with IDA
        assert idaapi.register_action(action_desc), "Action registration failed"

    
    def _del_action_hash_lookup(self):
        idaapi.unregister_action(self.ACTION_HASH_LOOKUP)


    def _del_action_set_xor(self):
        idaapi.unregister_action(self.ACTION_SET_XOR)


    def _del_action_hunt(self):
        idaapi.unregister_action(self.ACTION_HUNT)
    #--------------------------------------------------------------------------
    # Initialize Hooks
    #--------------------------------------------------------------------------

    def _init_hooks(self):
        """
        Install plugin hooks into IDA.
        """
        self._hooks = Hooks()
        self._hooks.ready_to_run = self._init_hexrays_hooks
        self._hooks.hook()


    def _init_hexrays_hooks(self):
        """
        Install Hex-Rays hooks (when available).
        NOTE: This is called when the ui_ready_to_run event fires.
        """
        if idaapi.init_hexrays_plugin():
            idaapi.install_hexrays_callback(self._hooks.hxe_callback)


#------------------------------------------------------------------------------
# Plugin Hooks
#------------------------------------------------------------------------------
class Hooks(idaapi.UI_Hooks):

    def finish_populating_widget_popup(self, widget, popup):
        """
        A right click menu is about to be shown. (IDA 7)
        """
        inject_actions(widget, popup, idaapi.get_widget_type(widget))
        return 0

    def hxe_callback(self, event, *args):
        """
        HexRays event callback.
        We lump this under the (UI) Hooks class for organizational reasons.
        """

        #
        # if the event callback indicates that this is a popup menu event
        # (in the hexrays window), we may want to install our menu
        # actions depending on what the cursor right clicked.
        #

        if event == idaapi.hxe_populating_popup:
            form, popup, vu = args

            idaapi.attach_action_to_popup(
                form,
                popup,
                HashDB_Plugin_t.ACTION_HASH_LOOKUP,
                "HashDB Lookup",
                idaapi.SETMENU_APP,
            )
            idaapi.attach_action_to_popup(
                form,
                popup,
                HashDB_Plugin_t.ACTION_SET_XOR,
                "HashDB set XOR key",
                idaapi.SETMENU_APP,
            )
            idaapi.attach_action_to_popup(
                form,
                popup,
                HashDB_Plugin_t.ACTION_HUNT,
                "HashDB Hunt Algorithm",
                idaapi.SETMENU_APP,
            )

        # done
        return 0

#------------------------------------------------------------------------------
# Prefix Wrappers
#------------------------------------------------------------------------------
def inject_actions(form, popup, form_type):
    """
    Inject actions to popup menu(s) based on context.
    """

    #
    # disassembly window
    #

    if (form_type == idaapi.BWN_DISASMS) or (form_type == idaapi.BWN_PSEUDOCODE):
        # insert the action entry into the menu
        #

        idaapi.attach_action_to_popup(
            form,
            popup,
            HashDB_Plugin_t.ACTION_HASH_LOOKUP,
            "HashDB Lookup",
            idaapi.SETMENU_APP
        )

        idaapi.attach_action_to_popup(
            form,
            popup,
            HashDB_Plugin_t.ACTION_SET_XOR,
            "HashDB set XOR key",
            idaapi.SETMENU_APP
        )

        idaapi.attach_action_to_popup(
            form,
            popup,
            HashDB_Plugin_t.ACTION_HUNT,
            "HashDB Hunt Algorithm",
            idaapi.SETMENU_APP
        )

    # done
    return 0

#------------------------------------------------------------------------------
# IDA ctxt
#------------------------------------------------------------------------------

class IDACtxEntry(idaapi.action_handler_t):
    """
    A basic Context Menu class to utilize IDA's action handlers.
    """

    def __init__(self, action_function):
        idaapi.action_handler_t.__init__(self)
        self.action_function = action_function

    def activate(self, ctx):
        """
        Execute the embedded action_function when this context menu is invoked.
        """
        self.action_function()
        return 1

    def update(self, ctx):
        """
        Ensure the context menu is always available in IDA.
        """
        return idaapi.AST_ENABLE_ALWAYS


#--------------------------------------------------------------------------
# Plugin Registration
#--------------------------------------------------------------------------

# Global flag to ensure plugin is only initialized once
p_initialized = False

# Register IDA plugin
def PLUGIN_ENTRY():
    return HashDB_Plugin_t()
