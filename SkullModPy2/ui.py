import os

import wx
import wx.adv

from SkullModPy2.app_info import *
from SkullModPy2.resources import *
from SkullModPy2.util import get_data_directory, human_readable_file_size
from SkullModPy2.gfs import GfsMetadataEntry, get_metadata, get_files_in_dir, write_content, export_files


class InternalListCtrlPanel(wx.Panel):
    def __init__(self, parent):
        wx.Panel.__init__(self, parent, wx.ID_ANY)
        resizer = wx.BoxSizer(wx.HORIZONTAL)
        self.internal_grid_string_table = InternalListCtrl(parent=self, style=wx.LC_REPORT)
        resizer.Add(self.internal_grid_string_table, 1, wx.EXPAND | wx.ALL)
        self.SetSizerAndFit(resizer)


class InternalListCtrl(wx.ListCtrl):
    def __init__(self, *args, **kwargs):
        wx.ListCtrl.__init__(self, *args, **kwargs)
        self.InsertColumn(0, 'Path', width=400)
        self.InsertColumn(1, 'Size', width=100)

    def set_data(self, data: list[GfsMetadataEntry]):
        self.DeleteAllItems()
        if data is None:
            return
        self.Freeze()
        for y in range(len(data)):
            self.InsertItem(y, data[y].local_path)
            self.SetItem(y, 1, human_readable_file_size(data[y].size))
        self.Thaw()


class FileExplorerPanel(wx.Panel):
    def __init__(self, parent):
        wx.Panel.__init__(self, parent, wx.ID_ANY)

        resizer = wx.BoxSizer(wx.HORIZONTAL)
        # Starting directory for directory view
        data_directory = get_data_directory()

        if data_directory is None:
            self.file_explorer = wx.GenericDirCtrl(self, wx.ID_ANY)
        else:
            self.file_explorer = wx.GenericDirCtrl(self, wx.ID_ANY, dir=data_directory)

        resizer.Add(self.file_explorer, 1, wx.EXPAND | wx.ALL)
        self.SetSizerAndFit(resizer)


class MainForm(wx.Frame):
    def __init__(self, *args, **kwargs):
        super(MainForm, self).__init__(*args, **kwargs)

        # Menubar
        menubar = wx.MenuBar()
        file_menu = wx.Menu()
        quit_item = file_menu.Append(wx.ID_EXIT, 'Quit', 'Quit application')
        self.Bind(wx.EVT_MENU, self.on_quit, quit_item)

        info_menu = wx.Menu()
        info_menu.Append(wx.ID_ABOUT, 'About')
        info_menu.Bind(wx.EVT_MENU, MainForm.on_about_box)

        menubar.Append(file_menu, '&File')
        menubar.Append(info_menu, 'Info')

        self.SetMenuBar(menubar)

        # Content
        splitter = wx.SplitterWindow(self)
        self.panel1 = FileExplorerPanel(splitter)
        self.panel2 = InternalListCtrlPanel(splitter)

        splitter.SplitVertically(self.panel1, self.panel2, -550)
        tree = self.panel1.file_explorer.GetTreeCtrl()
        self.Bind(wx.EVT_TREE_ITEM_RIGHT_CLICK, self.on_right_click, tree)
        self.Bind(wx.EVT_TREE_SEL_CHANGED, self.on_sel_changed, tree)

        # Popup menus
        self.popupmenu_unpack = wx.Menu()
        self.popupmenu_pack = wx.Menu()
        unpack_entry = self.popupmenu_unpack.Append(-1, 'Unpack GFS')
        pack_entry = self.popupmenu_pack.Append(-1, 'Pack directory')
        pack_entry_aligned = self.popupmenu_pack.Append(-1, 'Pack directory (aligned)')
        refresh_tree_pack = self.popupmenu_pack.Append(-1, 'Refresh')
        refresh_tree_unpack = self.popupmenu_unpack.Append(-1, 'Refresh')
        self.Bind(wx.EVT_MENU, self.on_unpack, unpack_entry)
        self.Bind(wx.EVT_MENU, self.on_pack, pack_entry)
        self.Bind(wx.EVT_MENU, self.on_pack_aligned, pack_entry_aligned)
        self.Bind(wx.EVT_MENU, self.refresh_tree, refresh_tree_pack)
        self.Bind(wx.EVT_MENU, self.refresh_tree, refresh_tree_unpack)
        self.current_target = None

        # Window
        self.SetSize((1000, 550))
        self.SetIcon(SKM2.GetIcon())
        self.SetTitle(APPLICATION_NAME + ' ' + APPLICATION_VERSION)

    def on_quit(self, e):
        self.Close()

    def on_pack(self, e):
        self.pack(False)

    def on_pack_aligned(self, e):
        self.pack(True)

    def pack(self, aligned):
        target_export_path = self.current_target + '.gfs'
        # Check if there is a directory
        if os.path.isdir(target_export_path):
            dialog = wx.MessageDialog(self, 'Cannot create .gfs file, there is a directory with the target name', 'Error', style=wx.OK)
            dialog.ShowModal()
            return
        # Check if target file exists and ask for overwrite
        if os.path.isfile(target_export_path):
            dialog = wx.MessageDialog(self, 'Do you want to overwrite the existing .gfs file?', 'Warning', wx.YES_NO | wx.NO_DEFAULT)
            replace = dialog.ShowModal() == wx.ID_YES
            if not replace:
                return
        # Check if total of files is more than 3 GB
        file_entries = get_files_in_dir(self.current_target)
        if sum(entry.size for entry in file_entries) > 3000000000:
            dialog = wx.MessageDialog(self, 'Total data is more than 3 GB, continue?', 'Warning', wx.YES_NO | wx.NO_DEFAULT)
            if dialog.ShowModal() == wx.ID_NO:
                return
        # Write file
        write_content(self.current_target, file_entries, aligned)
        # Update tree
        self.Freeze()
        self.panel1.file_explorer.ReCreateTree()
        self.panel1.file_explorer.SetPath(target_export_path)
        self.Thaw()

    def on_unpack(self, e):
        # Check if target file is a valid gfs file
        try:
            # Get metadata
            metadata = get_metadata(self.current_target)
            if metadata is None:
                raise ValueError('Not a valid .gfs file')
        except:
            dialog = wx.MessageDialog(self, 'Not a valid .gfs file', 'Error')
            dialog.ShowModal()
            return
        # Make base directory
        base_dir = os.path.splitext(self.current_target)[0]
        if os.path.exists(base_dir):
            if os.path.isdir(base_dir):
                dialog = wx.MessageDialog(self, 'Directory already exists, replace files?', 'Question', wx.YES_NO | wx.NO_DEFAULT)
                if dialog.ShowModal() == wx.NO:
                    return
            else:
                dialog = wx.MessageDialog(self, 'File with target unpack name already exists', 'Error')
                dialog.ShowModal()
                return
        os.makedirs(base_dir, exist_ok=True)
        # Unpack
        try:
            if not export_files(self.current_target, metadata):
                raise ValueError('Invalid path or other error')
        except:
            dialog = wx.MessageDialog(self, 'Error during unpack', 'Error')
            dialog.ShowModal()
        # Update tree
        self.Freeze()
        self.panel1.file_explorer.ReCreateTree()
        self.panel1.file_explorer.SetPath(base_dir)
        self.Thaw()

    def refresh_tree(self, e):
        path = self.panel1.file_explorer.GetPath()
        file = self.panel1.file_explorer.GetFilePath()
        self.Freeze()
        self.panel1.file_explorer.ReCreateTree()
        if path != '':
            self.panel1.file_explorer.SetPath(path)
        if file != '':
            self.panel1.file_explorer.SetPath(file)
        self.Thaw()

    @staticmethod
    def on_about_box(e):
        about_dialog_info = wx.adv.AboutDialogInfo()
        about_dialog_info.SetIcon(SKM2.GetIcon())
        about_dialog_info.SetName(APPLICATION_NAME)
        about_dialog_info.SetVersion(APPLICATION_VERSION + ' ' + APPLICATION_DATE)
        about_dialog_info.SetDescription('Unofficial modding tool for Skullgirls')
        about_dialog_info.SetLicense(APPLICATION_LICENSE)
        wx.adv.AboutBox(about_dialog_info)

    def on_right_click(self, event):
        # Select element before triggering menu
        tree_ctrl = self.panel1.file_explorer.GetTreeCtrl()
        selected_item, _ = tree_ctrl.HitTest(event.GetPoint())
        tree_ctrl.SelectItem(selected_item)

        if self.panel1.file_explorer.GetFilePath() == '':
            if self.panel1.file_explorer.GetPath() == '':
                return
            else:
                self.current_target = self.panel1.file_explorer.GetPath()
        else:
            self.current_target = self.panel1.file_explorer.GetFilePath()

        if os.path.isfile(self.current_target):
            self.PopupMenu(self.popupmenu_unpack, event.GetPoint())

        # Don't allow the root of a partition to be selected
        if os.path.isdir(self.current_target) and os.path.dirname(self.current_target) != self.current_target:
            self.PopupMenu(self.popupmenu_pack, event.GetPoint())

    def on_sel_changed(self, event):
        if not self.panel1.file_explorer.IsBeingDeleted():
            table = self.panel2.internal_grid_string_table
            table.set_data(get_metadata(self.panel1.file_explorer.GetFilePath()))
