import c4d
import os
from c4d import gui
import json

# Romain Weeger - www.wexample.com
# The MIT License (MIT), see LICENSE for details
# If you enjoy this plugin, please
# contact me, and say me hello \o/

# - Object must be a standard C4D R15 character
# - Controllers objects must not have been renamed
# - Character is a cartoon with 3 "non thumbs" fingers on each hand
# - Character has scapula and no toes
# - Character has as simple head bone

PLUGIN_ID = 1032236
VERSION = '1.0'
BUTTON_COPY = 1000
BUTTON_PASTE = 1001
TEXT_COPYRIGHT = 1002
COMBO_TYPE = 1003
COPY_TYPE_FULL = 0
COPY_TYPE_SELECTED = 1
FINGERS_NUMBER = 3
CHARACTER_OBJECT_ID = 1021433
DATA_WATERMARK = '[wPoseCloner data]'
TEXT_COPYRIGHT_TEXT = 'Romain Weeger - 2014 - www.wexample.com'


def component_controllers(name, fingers_count=0):
    if name == 'head':
        return [
            'Head_con+',
            'Neck_con+'
        ]
    elif name == 'torso':
        return [
            'Chest_con+',
            'Hips_con+',
            'FK_Pelvis_con+',
            'FK_Spine_01_con+',
            'FK_Spine_02_con+',
            'FK_Spine_03_con+',
            'Torso_con+'
        ]
    elif name == 'l_arm':
        return component_controllers_arm('L')
    elif name == 'r_arm':
        return component_controllers_arm('R')
    elif name == 'l_fingers':
        return component_controllers_fingers('L', fingers_count)
    elif name == 'r_fingers':
        return component_controllers_fingers('R', fingers_count)
    elif name == 'l_leg':
        return component_controllers_leg('L')
    elif name == 'r_leg':
        return component_controllers_leg('R')


def component_controllers_leg(side):
    return [
        side + '_IK_Leg_nb_con+',
        side + '_Foot_nb_con+',
        side + '_NB_IK_Leg_PV_con+',
    ]


def component_controllers_arm(side):
    return [
        side + '_Collar_con+',
        side + '_PV_con+',
        side + '_IK_Arm_nb_con+',
        side + '_Hand_nb_con+',
    ]


def component_controllers_fingers(side, length):
    fingers_controllers = []
    # Thumb
    fingers_controllers += [
        side + '_Thumb_Palm_Base_con+',
        side + '_Thumb_Curl_con+',
        side + '_Thumb_Seg1_jnt_con+',
        side + '_Thumb_Seg2_jnt_con+',
    ]
    # Create list of fingers controllers
    for i in range(0, length):
        # First item has no suffx
        suffix = ''
        # Other have _X number
        if i != 0:
            suffix = '_' + str(i)
        # Generate names list.
        fingers_controllers = fingers_controllers + [
            side + '_Finger_Palm_Base_con+' + suffix,
            side + '_Finger_Curl_con+' + suffix,
            side + '_Finger_Seg1_jnt_con+' + suffix,
            side + '_Finger_Seg2_jnt_con+' + suffix,
            side + '_Finger_Seg3_jnt_con+' + suffix,
        ]
    # Return list.
    return fingers_controllers


def controllers_list(object_root):
    fingers_count = object_count_fingers(object_root)

    controllers = component_controllers('head')
    controllers += component_controllers('torso')
    controllers += component_controllers('l_arm')
    controllers += component_controllers('r_arm')
    controllers += component_controllers('l_fingers', fingers_count)
    controllers += component_controllers('r_fingers', fingers_count)
    controllers += component_controllers('l_leg')
    controllers += component_controllers('r_leg')

    return controllers


def object_next(op):
    if op is None:
        return None

    if op.GetDown():
        return op.GetDown()

    while not op.GetNext() and op.GetUp():
        op = op.GetUp()

    return op.GetNext()


def object_find_controllers_root(object_start):
    if object_start is None:
        gui.MessageDialog('Object selection not valid (character root or controller).')
        return False
    # Search if object is parent itself or if
    # is some of children if current selected is a parent object (character rig for example).
    object_search = object_start
    while object_search:
        if object_find_controllers_root_check(object_search):
            # Object root found
            return object_search
        else:
            object_search = object_next(object_search)
    # Not found... now search to parents chain
    object_search = object_start.GetUp()
    while object_search:
        # First test if we don't go out a character object, which is a limit for search
        if object_search.CheckType(CHARACTER_OBJECT_ID):
            return False
        elif object_find_controllers_root_check(object_search):
            return object_search
        else:
            object_search = object_search.GetUp()
    return False


def object_find_controllers_root_check(object_search):
    return isinstance(object_search, c4d.BaseObject) and object_search.GetName() == 'Root_null'


def object_count_fingers(object_controllers_root):
    # Detect fingers count
    fingers_count = 0
    object_search = object_controllers_root
    while object_search:
        if isinstance(object_search, c4d.BaseObject) and object_search.GetName().find('L_Finger_Controls') == 0:
            fingers_count += 1
        object_search = object_next(object_search)
    return fingers_count


def w_pose_cloner_copy(copy_type):
    object_selected = c4d.documents.GetActiveDocument().GetActiveObject()
    # Find controllers root used as parent saved controller
    object_controllers_root = object_find_controllers_root(object_selected)
    copied_part_name = 'null'

    if object_controllers_root is not False:
        output = {}
        # Create data package
        controllers = []

        if copy_type == COPY_TYPE_FULL:
            controllers = controllers_list(object_controllers_root)
            copied_part_name = 'Full pose'

        elif copy_type == COPY_TYPE_SELECTED:
            object_name = object_selected.GetName()
            # Get L or R
            side = object_name[:1]
            # Hand (fingers)
            if object_name[1:] == '_IK_Arm_nb_con+':
                controllers = component_controllers_fingers(side, object_count_fingers(object_controllers_root))
                copied_part_name = 'fingers ' + side
            # Arm
            elif object_name[1:] == '_Collar_con+' or object_name[1:] == '_PV_con+':
                controllers = component_controllers_arm(side)
                controllers += component_controllers_fingers(side, object_count_fingers(object_controllers_root))
                copied_part_name = 'arm and fingers ' + side
            # Leg
            elif object_name[1:] == '_NB_IK_Leg_PV_con+':
                controllers = component_controllers_leg(side)
                copied_part_name = 'leg ' + side
            # Controller only
            else:
                controllers_all = controllers_list(object_controllers_root)
                if object_name in controllers_all:
                    controllers = [object_name]
                    copied_part_name = 'controller ' + object_name

        print controllers
        for control_name in controllers:
            object_selected = object_controllers_root
            found = False
            while object_selected and found is False:
                if object_selected.GetName() == control_name:
                    found = True

                    # Coordinates names may not match with real w/y/z
                    # but used as indexes to save position and rotation
                    # in the same time.
                    output[control_name] = {
                        'x': object_selected[c4d.ID_BASEOBJECT_REL_POSITION][0],
                        'y': object_selected[c4d.ID_BASEOBJECT_REL_POSITION][1],
                        'z': object_selected[c4d.ID_BASEOBJECT_REL_POSITION][2],
                        'h': object_selected[c4d.ID_BASEOBJECT_REL_ROTATION][0],
                        'p': object_selected[c4d.ID_BASEOBJECT_REL_ROTATION][1],
                        'b': object_selected[c4d.ID_BASEOBJECT_REL_ROTATION][2],
                    }
                object_selected = object_next(object_selected)
            # Control not found, throw a console warning in full mode only
            if copy_type == COPY_TYPE_FULL and found is False:
                print 'Not found : ' + control_name
        # Copy data
        c4d.CopyStringToClipboard(DATA_WATERMARK + json.dumps(output))
        message = 'Pose copied to clipboard : ' + copied_part_name
        #gui.MessageDialog(message)
        print message
    return


def w_pose_cloner_paste():
    # Retrieve from clipboard
    data = c4d.GetStringFromClipboard()
    # Check if valid data has been saved
    if data[0:len(DATA_WATERMARK)] != DATA_WATERMARK:
        gui.MessageDialog('No valid pose saved to clipboard.')
        return
    # Remove watermark.
    data = data[len(DATA_WATERMARK):]
    # Get selected object.
    object_selected = c4d.documents.GetActiveDocument().GetActiveObject()
    # Find controllers root
    object_controllers_root = object_find_controllers_root(object_selected)
    if object_controllers_root is not False:

        data = json.loads(data)

        for control_name in data:
            object_selected = object_controllers_root
            found = False

            while object_selected and found is False:
                if object_selected.GetName() == control_name:
                    found = True

                    object_selected.SetRelPos(
                        c4d.Vector(data[control_name]['x'], data[control_name]['y'], data[control_name]['z']))
                    object_selected.SetRelRot(
                        c4d.Vector(data[control_name]['h'], data[control_name]['p'], data[control_name]['b']))
                    c4d.EventAdd()
                object_selected = object_next(object_selected)
            # Control not found
            if found is False:
                print 'Not found : ' + control_name
        # gui.MessageDialog('Pose applied')
    return


class WPoseClonerDialog(c4d.gui.GeDialog):
    doc = None
    copy_type = COPY_TYPE_FULL

    def CreateLayout(self):
        self.AddComboBox(id=COMBO_TYPE, flags=c4d.BFH_CENTER, initw=400)
        self.AddChild(id=COMBO_TYPE, subid=0, child='Full character pose')
        self.AddChild(id=COMBO_TYPE, subid=1, child='Selected member (auto detect)')
        self.AddButton(id=BUTTON_COPY, flags=c4d.BFH_SCALE, initw=400, name="Copy pose")
        self.AddButton(id=BUTTON_PASTE, flags=c4d.BFH_SCALE, initw=400, name="Paste pose")
        self.AddStaticText(id=TEXT_COPYRIGHT, flags=c4d.BFH_CENTER, initw=400, name=TEXT_COPYRIGHT_TEXT)
        return True

    # React to user's input:
    def Command(self, id, msg):
        if id == BUTTON_COPY:
            w_pose_cloner_copy(self.copy_type)
        elif id == BUTTON_PASTE:
            w_pose_cloner_paste()
        elif id == COMBO_TYPE:
            self.copy_type = self.GetInt32(COMBO_TYPE)
        return True


class wPoseClonerCommand(c4d.plugins.CommandData):
    dialog = None

    def Execute(self, doc):
        if self.dialog is None:
            self.dialog = WPoseClonerDialog()

        return self.dialog.Open(dlgtype=c4d.DLG_TYPE_ASYNC, pluginid=PLUGIN_ID, defaultw=400, xpos=-1,
                                ypos=-1)

    def RestoreLayout(self, sec_ref):
        if self.dialog is not None:
            return self.dialog.Restore(pluginid=PLUGIN_ID, secret=sec_ref)


if __name__ == "__main__":
    dir, file = os.path.split(__file__)
    icon = c4d.bitmaps.BaseBitmap()
    icon.InitWith(os.path.join(dir, "res", "icon.tif"))
    c4d.plugins.RegisterCommandPlugin(
        id=PLUGIN_ID,
        str="wPoseCloner",
        info=0,
        help="...",
        dat=wPoseClonerCommand(),
        icon=icon)