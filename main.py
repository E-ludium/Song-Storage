"""Project Name: SongStorage
   Project ID: 9
   Project Difficulty: A
   Propose: NIP
"""


# GUI-related imports
from tkinter import *
from tkinter import ttk
from tkinter import filedialog
from tkinter import messagebox
from functools import partial

# Specialized tools for working with databases and configuration files
import configparser
import sqlite3
from sqlite3 import Error

# Specialized methods for working with files and directories
import os
from os import path
import ntpath
import shutil
import zipfile

# 3rd party library for playing audio files
from pydub import AudioSegment
from pydub.playback import play

# Library for enabling multithreading
import _thread

# Library that allows system calls
import sys


# Variables tasked with processing the configuration file of the application
config_var = configparser.ConfigParser()  # We will use a config file to store the path of the media folder
config_var.read('config.ini')

option = ""  # Variable that will store user choice in CLI-commands that require a "Yes" or "No" answer


def connect_to_database():
    """
        This method attempts a connection to the application's database, returning the connection if successful

        :return connection: Returns the variable pointing to the connection to the database.
    """

    # Attempting a connection to the database
    try:
        temp_connection = sqlite3.connect('Resources/media.db')
    except Error:
        print("Error: Could not connect to the database. Make sure the file \"media.db\" is located inside the "
              "\"Resources\" folder.")
        return False

    if config_var['RUN-MODE']['run_mode'] == "2":  # Debugging mode
        print("\nSuccessfully connected to the database.")

    # The variable storing the SQL command for creating the "media" table
    create_table = """ CREATE TABLE IF NOT EXISTS media (
                        id integer PRIMARY KEY,
                        title text NOT NULL,
                        artist text NOT NULL,
                        album text,
                        release_date DATE,
                        tags TEXT,
                        mode BIT default 0 NOT NULL,
                        full_path text NOT NULL UNIQUE
                        ); """

    # Attempting to create the "media" table if it doesn't exist already
    try:
        cursor = temp_connection.cursor()
        cursor.execute(create_table)
        temp_connection.commit()
        cursor.close()
    except Error as e:
        print("Error: Could not create the table.")
        print(e)
        return False

    if config_var['RUN-MODE']['run_mode'] == "2":  # Debugging mode
        print("\nThe media table exists or has been created successfully..")

    # Returning the connection variable so that it can be used by other features of the application
    return temp_connection


def add_media(file, mode, gui_instance=None):
    """
        Adds the file specified as parameter to the database.

        :param file: the file to be added to the database
        :param mode: the mode in which the algorithm runs.
                     '0' means the user is trying to copy a media file from another source folder.
                     '1' means the current file is already present in the media folder, but it's not indexed by the
                     database (this can happen if, for example, the user has manually placed a media file inside
                     the media folder).
        :param gui_instance: Specifies whether the method was called from a CLI or from a GUI instance. The latter
                             means the method will process some GUI-related elements such as widgets or windows.

        :return True: The method has successfully added the media file both to the media folder and to the database.
        :return False: There was an error when trying to add the media file, or the file already exists.
    """

    global option  # Using the global variable that specifies user choice (typically "Yes" or "No" choices)
    global config_var  # Using the global variable that reads and modifies the configuration file

    basename_file = os.path.basename(file)

    # Checking if the specified file is a valid media file
    if basename_file.endswith('.mp3') or basename_file.endswith('.wav'):
        assumed_artist = ""  # This variable will store the artist of the media

        if "-" in basename_file:

            """ 
                Usually, media files use a '-' character to split the title of the media and the artist.
                This algorithm will attempt to automatically 'guess' the title and artist of the media if this
                character is present.
            """

            # If there is a whitespace before the '-' character, we remove it
            if basename_file.split("-")[0].endswith(" "):
                assumed_artist = basename_file.split("-")[0][:-1]  # The auto-processed artist name
            else:
                assumed_artist = basename_file.split("-")[0]

            if file.split("-")[1].startswith(" "):  # If there is a whitespace after the '-' character, we remove it
                assumed_title = basename_file.split("-")[1][1:-4]  # The auto-processed media title
            else:
                assumed_title = basename_file.split("-")[1][:-4]

        else:  # If no "-" character is present in the title of the file, assuming the title is the name of the file
            assumed_title = os.path.splitext(basename_file)[0]

        if config_var['RUN-MODE']['run_mode'] == "2":  # Debugging mode
            print("\nAssumed title: " + assumed_title)
            print("Assumed artist: " + assumed_artist)

        if not mode:  # The user is attempting to add media files from another directory
            try:
                shutil.copy2(file, media_folder)  # Copying the source file to the media folder

            except PermissionError:  # Application does not have permission to write in the media folder
                # Application is running in GUI-mode
                if gui_instance is not None:
                    messagebox.showerror("Unable to copy file", "Unable to copy file to media folder. Make sure you "
                                         "haven't selected a write-protected folder.")

                # Application is running in CLI or debugging mode
                if config_var['RUN-MODE']['run_mode'] == "1" or config_var['RUN-MODE']['run_mode'] == "2":
                    print("\nError: Unable to copy file to media folder. Make sure you haven't selected a "
                          "write-protected folder.")

                return False

        # Updating the database
        cursor = connection.cursor()

        # Getting the full path of the file (using an app-level convention for slashes)
        full_path = os.path.join(media_folder, os.path.basename(file)).replace("\\", "/")

        cursor.execute("SELECT COUNT(1) FROM media WHERE full_path = \"" + full_path + "\"")
        result = int(str(cursor.fetchone())[1])

        if not result:  # The selected file is not present in the database
            sql_command = ''' INSERT INTO media(title, artist, album, release_date, tags, full_path)
                            VALUES (?, ?, ?, ?, ?, ?) '''

            values = (assumed_title, assumed_artist, '', '', '', full_path)

            try:  # Attempting to add the media file to the database
                cursor.execute(sql_command, values)

                connection.commit()

            except Error:  # Database is locked
                # Application is running in GUI-mode
                if gui_instance is not None:
                    messagebox.showerror("Database is locked", "Error when trying to commit changes to database. Make "
                                         "sure another application is not using the database.")

                # Application is running in CLI or debugging mode
                if config_var['RUN-MODE']['run_mode'] == "1" or config_var['RUN-MODE']['run_mode'] == "2":
                    print("\nError when trying to commit changes to database. Make sure another application is not "
                          "using the database.")

                return False

            if gui_instance is not None:  # The method has been fired by a GUI widget
                gui_instance.display_media()  # Updating the media list

            else:  # The method has been fired by using CLI
                cursor.execute("SELECT id FROM media WHERE full_path = \"" + full_path + "\"")
                new_id = cursor.fetchone()

                print("\nThe song was added successfully!\n\nThe ID of the song is: " + str(new_id[0]) +
                      "\nDo you want to configure the song metadata now? (Y/N)")

                option = input()  # Getting user response
                if option.lower() == "y":  # The user has responded affirmatively
                    SongStorageCLI.configure_media(full_path)

                else:  # The user has responded negatively
                    print("\nThe auto-processing tool assumed that the name of the song is \"" + assumed_title + "\" " +
                          "and that the name of the artist is \"" + assumed_artist + "\".\nYou can always change " +
                          "these values, as well as other metadata information, by using the \"Modify_data " +
                          str(new_id[0]) + "\" command.")
                    return

        else:  # The selected file already exists in the database; letting the user know
            if gui_instance is not None:  # The method has been fired by a GUI widget
                messagebox.showinfo("Media file already exists",
                                    "The selected file already exists in the media folder.")

            else:  # The method has been fired by using CLI
                print("There is already a song with this name in the media folder!")

            return False

        if config_var['RUN-MODE']['run_mode'] == "2":  # Debugging mode
            print("\nMedia file has been added successfully.")

        return True


def play_media(media, allow_multiprocessing, gui_instance=None):
    """
        Plays the media file specified as parameter.

        :param media: The media file to be played.
        :param allow_multiprocessing: Checks whether application can spawn a new thread to play music in background.
        :param gui_instance: Specifies whether the method was called from a CLI or from a GUI instance. The latter
                             means the method will process some GUI-related elements such as widgets or windows.
        :return: None
    """

    cursor = connection.cursor()

    # CLI-only method: The user has attempted to play the media file based on its ID in the database
    if media.isnumeric():
        cursor.execute("SELECT full_path FROM media WHERE id = " + media)

        full_path = cursor.fetchone()

        if full_path is None:  # The system couldn't find the specified ID
            print("\nError: The specified ID does not exist in the database.")
            return

        full_path = full_path[0]

    else:  # The method is fired by the GUI or the user has attempted to play the media file by using its name
        full_path = os.path.join(media_folder, os.path.basename(media)).replace("\\", "/")

        if not path.exists(full_path):  # (CLI-only) The user has provided an invalid filename
            print("\nError: The specified media file does not exist.")
            return

    # Attempting to play the media file
    if full_path.endswith(".mp3"):  # The target file is an .mp3 media file
        try:
            media_file = AudioSegment.from_mp3(full_path)

            if allow_multiprocessing:  # If the application runs in loop mode, we can use multithreading
                _thread.start_new_thread(play, (media_file,))

            else:  # The application runs in only one iteration, no multithreading is possible
                play(media_file)

        except FileNotFoundError:  # Could not play the media file
            if gui_instance is not None:  # Application is running in GUI-mode
                messagebox.showerror("Unable to play file", "Unable to play media file. Please make sure that you have "
                                     "ffmpeg installed (https://ffmpeg.org/) and that the files \"ffmpeg.exe\", "
                                     "\"ffplay.exe\" and \"ffprobe.exe\" are also copied in the current folder of the "
                                     "application.")

            # Application is running in CLI or debugging mode
            if config_var['RUN-MODE']['run_mode'] == "1" or config_var['RUN-MODE']['run_mode'] == "2":
                print("\nError: Unable to play media file. Please make sure that you have ffmpeg installed "
                      "(https://ffmpeg.org/) and that the files \"ffmpeg.exe\", \"ffplay.exe\" and \"ffprobe.exe\" are "
                      "also copied in the current folder of the application.")

            return

    elif full_path.endswith(".wav"):  # The target file is a .wav media file
        try:
            media_file = AudioSegment.from_wav(full_path)

            if allow_multiprocessing:  # If the application runs in loop mode, we can use multithreading
                _thread.start_new_thread(play, (media_file,))

            else:  # The application runs in only one iteration, no multithreading is possible
                play(media_file)

        except FileNotFoundError:  # Could not play the media file
            if gui_instance is not None:  # Application is running in GUI-mode
                messagebox.showerror("Unable to play file", "Unable to play media file. Please make sure that you have "
                                     "ffmpeg installed (https://ffmpeg.org/) and that the files \"ffmpeg.exe\", "
                                     "\"ffplay.exe\" and \"ffprobe.exe\" are also copied in the current folder of the "
                                     "application.")

            # Application is running in CLI or debugging mode
            if config_var['RUN-MODE']['run_mode'] == "1" or config_var['RUN-MODE']['run_mode'] == "2":
                print("\nError: Unable to play media file. Please make sure that you have ffmpeg installed "
                      "(https://ffmpeg.org/) and that the files \"ffmpeg.exe\", \"ffplay.exe\" and \"ffprobe.exe\" are "
                      "also copied in the current folder of the application.")

            return

    if config_var['RUN-MODE']['run_mode'] == "2":  # Debugging mode
        print("\nThe media file is playing.")


def remove_media(media, window=None, gui_instance=None):
    """
        Removes the media given as parameter from the database and from the media folder.

        :param media: The path to the media file to be removed.
        :param window: The window which will need to close after database update.
        :param gui_instance: Specifies whether the method was called from a CLI or from a GUI instance. The latter
                             means the method will process some GUI-related elements such as widgets.

        :return True: The method has successfully removed the media file from the media folder and the database.
        :return False: There was an error when trying to remove the media file.
    """

    cursor = connection.cursor()

    if media.isnumeric():  # CLI-only: The user has attempted to delete the media file based on its ID in the database
        cursor.execute("SELECT full_path FROM media WHERE id = " + media)

        full_path = cursor.fetchone()

        if full_path is None:  # The system couldn't find the specified ID
            print("Error: The specified ID does not exist in the database.")
            return

        # Attempting to remove the media file record from the database
        try:
            cursor.execute("DELETE FROM media WHERE id = " + media)  # Deleting the record from the database

            connection.commit()  # Writing the changes to the database

        except Error:  # Database is locked
            print("\nError when trying to commit changes to database. Make sure another application is not using the "
                  "database.")

            return False

        cursor.close()

        # Attempting to re-order the keys after the deleted one
        if not resort_keys(media):  # Fatal error: database is locked
            print("\nERROR: DATABASE COULD NOT BE UPDATED. APPLICATION CANNOT WORK AS INTENDED. "
                  "PLEASE MANUALLY REMOVE ALL MEDIA FILES FROM THE MEDIA FOLDER AND TRY ADDING THEM BACK.")
            sys.exit()  # Quitting; the application will malfunction until the user manually resets the media folder

        try:
            os.remove(full_path[0].replace("\\", "/"))  # Removes the media file from the media folder

        except FileNotFoundError:
            print("\nError: Could not remove the file from the media folder: The file does not exist.")
            return False

        except PermissionError:
            print("\nError: Unable to remove file from the media folder. Make sure you haven't selected a "
                  "write-protected folder. If the issue persists, try changing the media folder and manually removing"
                  " the media file from the current media folder.")
            return False

        print("\nThe media file has been removed.")

    else:  # The user is either using the GUI or has provided the filename as parameter
        # Getting the full path of the file (using an app-level convention for slashes)
        full_path = os.path.join(media_folder, os.path.basename(media)).replace("\\", "/")

        if path.exists(full_path):  # (CLI-only) Checking if the provided filename exists

            # Getting the id of the media which will be removed in order to re-order the IDs of the database
            cursor.execute("SELECT id FROM media WHERE full_path = " + "\"" + full_path + "\"")
            id_value = cursor.fetchone()

            # Attempting to remove the media file record from the database
            try:
                cursor.execute("DELETE FROM media WHERE full_path = " + "\"" + full_path + "\"")

                connection.commit()  # Writing the changes to the database

            except Error:  # Database is locked
                # Application is running in GUI-mode
                if gui_instance is not None:
                    messagebox.showerror("Database is locked", "Error when trying to commit changes to database. Make "
                                                               "sure another application is not using the database.")

                # Application is running in CLI or debugging mode
                if config_var['RUN-MODE']['run_mode'] == "1" or config_var['RUN-MODE']['run_mode'] == "2":
                    print("\nError when trying to commit changes to database. Make sure another application is not "
                          "using the database.")

                return False

            cursor.close()

            # Attempting to re-order the keys after the deleted one
            if not resort_keys(id_value[0]):  # Fatal error: database is locked
                # Application is running in GUI-mode
                if gui_instance is not None:
                    messagebox.showerror("Database error", "DATABASE COULD NOT BE UPDATED. APPLICATION CANNOT WORK AS "
                                         "INTENDED. PLEASE MANUALLY REMOVE ALL MEDIA FILES FROM THE MEDIA FOLDER AND "
                                         "TRY ADDING THEM BACK.")
                    # Quitting; the application will malfunction until the user manually resets the media folder
                    sys.exit()

                # Application is running in CLI or debugging mode
                if config_var['RUN-MODE']['run_mode'] == "1" or config_var['RUN-MODE']['run_mode'] == "2":
                    print("\nERROR: DATABASE COULD NOT BE UPDATED. APPLICATION CANNOT WORK AS INTENDED. "
                          "PLEASE MANUALLY REMOVE ALL MEDIA FILES FROM THE MEDIA FOLDER AND TRY ADDING THEM BACK.")
                    # Quitting; the application will malfunction until the user manually resets the media folder
                    sys.exit()

            try:
                os.remove(full_path)  # Removes the media file from the media folder

            except FileNotFoundError:
                # Application is running in GUI-mode
                if gui_instance is not None:
                    messagebox.showerror("File not found", "The file does not exist.")

                # Application is running in CLI or debugging mode
                if config_var['RUN-MODE']['run_mode'] == "1" or config_var['RUN-MODE']['run_mode'] == "2":
                    print("\nError: Could not remove the file from the media folder: The file does not exist.")

                return False

            except PermissionError:
                # Application is running in GUI-mode
                if gui_instance is not None:
                    messagebox.showerror("Unable to remove file", "Unable to remove file from the media folder. Make "
                                         "sure you haven't selected a write-protected folder. If the issue persists, "
                                         "try changing the media folder and manually removing the media file from the "
                                         "current media folder.")

                # Application is running in CLI or debugging mode
                if config_var['RUN-MODE']['run_mode'] == "1" or config_var['RUN-MODE']['run_mode'] == "2":
                    print("\nError: Unable to remove file from the media folder. Make sure you haven't selected a "
                          "write-protected folder. If the issue persists, try changing the media folder and manually "
                          "removing the media file from the current media folder.")

                return False

            if gui_instance is not None:  # The method has been fired by a GUI widget
                window.destroy()  # Closes the removal window

                # Reloading the media list of the root window
                gui_instance.library_items = []
                gui_instance.path_frame_parent.destroy()
                gui_instance.display_media()

            else:  # The method has been fired by using CLI
                print("\nThe media file has been removed.")

        else:  # (CLI-only) The user has provided an invalid filename
            print("\nError: The specified media file does not exist.")
            return False

    return True


def resort_keys(id_value):
    """
        Re-orders the keys of the database.

        :param id_value: The deleted key. All keys after this value need to be sorted.
        :return True: The database keys were succesfully sorted.
        :return False: Fatal error: The database keys could not be sorted. Application will malfunction until user
                       manually clears the media folder.
    """

    cursor = connection.cursor()

    try:
        cursor.execute("UPDATE media SET id = id - 1 WHERE id > " + str(id_value))

        connection.commit()

    except Error:  # Database is locked
        return False  # The error messages will be displayed by the caller method

    cursor.close()

    if config_var['RUN-MODE']['run_mode'] == "2":  # Debugging mode
        print("\nThe database keys were successfully sorted.")

    return True


def folder_selector(folder_path=None, gui_instance=None):
    """
        Prompts the user to select the media folder.

        :param folder_path: If the application is run in CLI-mode, the user can pass a path as an optional argument to
                            specify the new location of the media folder.
        :param gui_instance: Specifies whether the method was called from a CLI or from a GUI instance. The latter
                             means the method will process some GUI-related elements such as widgets.

        :return: True: The method has successfully updated the media folder.
        :return False: The configuration file was already in use or was manually removed; the operation failed.
    """

    global config_var  # Using the global variable that reads and modifies the configuration file

    if gui_instance is not None:  # The method has been fired by a GUI widget
        folder = filedialog.askdirectory()  # We will use an OS-specific dialog box call to select the media folder

        if folder != "":  # Checks to see if the user has canceled the operation
            config_var.set('MEDIA FOLDER', 'folder', folder)  # Updating the value inside the configuration file

            try:
                with open('config.ini', 'w') as configfile_folder:
                    config_var.write(configfile_folder)  # Writing the changes to the configuration file
                    configfile_folder.close()

            except IOError:
                messagebox.showerror("Writing to file failed", "Failed to write new value to the configuration file."
                                     " Please make sure no other applications are interacting with the configuration "
                                     "file and that \"config.ini\" is located in the folder of the application.")

                # Application is running in debugging mode
                if config_var['RUN-MODE']['run_mode'] == "2":
                    print("\nError: Failed to write new value to the configuration file. Please make sure no other "
                          "applications are interacting with the configuration file and that \"config.ini\" is located "
                          "in the folder of the application.")

                return False

            gui_instance.display_media_folder()  # Updating the media list

            gui_instance.folder_scan()

    else:  # The method has been fired by using CLI
        if not os.path.exists(folder_path):  # The user has specified an invalid folder
            print("\nError: The specified directory does not exist.")
            return False

        config_var.set('MEDIA FOLDER', 'folder', folder_path)  # Updating the value inside the configuration file

        try:
            with open('config.ini', 'w') as configfile_folder:
                config_var.write(configfile_folder)  # Writing the changes to the configuration file
                configfile_folder.close()

        except IOError:
            print("\nError: Failed to write new value to the configuration file. Please make sure no other "
                  "applications are interacting with the configuration file and that \"config.ini\" is located "
                  "in the folder of the application.")

            return False

        print("\nMedia folder updated.")

    return True


def intersection(list1, list2):
    """
        Performs an intersection of the values of the two lists specified as parameters. Returns a list containing
        only the shared values.

        :param list1: The first list.
        :param list2: The second list.
        :return: Returns a list containing only the common variables of the two lists passed as arguments.
    """

    list3 = []

    if not list1 and not list2:  # Both lists passed as arguments are empty
        return list3

    elif not list1 and list2:  # The first list passed as argument is empty
        return list2

    elif list1 and not list2:  # The second list passed as argument is empty
        return list1

    else:
        list3 = [value for value in list1 if value in list2]  # Getting only the common values of the two lists
        return list3


def load_cli(gui_instance):
    """
        Loads the application in command-line interface.

        :param gui_instance: The graphical user interface instance to be hidden.
        :return: None
    """

    gui_instance.destroy()  # Destroying the application graphical window

    SongStorageCLI(1)  # Loading the application in CLI, loop-mode


def load_gui():
    """
        Loads the graphical user interface of the application.

        :return: None
    """

    print("\nLoading graphical user interface...\n")
    SongStorageGUI().mainloop()


class SongStorageGUI(Tk):  # The GUI class responsible for showing the graphical interface to the user
    def __init__(self):
        """
            Initialization method of the class. Loads the main window and all graphical widgets to be used.

            :return: None
        """

        super().__init__()  # Loading the Tk window instance

        self.title("Song Storage")  # Naming the root window
        self.resizable(False, False)  # Disabling resizing of the root window
        self.iconphoto(True, PhotoImage(file="Resources/Icons/AppIcon.png"))  # Loading the icon of the application

        global config_var  # Using the global variable that reads and modifies the configuration file

        # Application's GUI was invoked from a CLI instance; updating the configuration file variable
        if config_var['RUN-MODE']['run_mode'] == "1":
            config_var.set('RUN-MODE', 'run_mode', "0")

            try:
                with open('config.ini', 'w') as configfile_gui:
                    config_var.write(configfile_gui)  # Writing the changes to the configuration file
                    configfile_gui.close()

            except IOError:
                messagebox.showerror("Writing to file failed", "Failed to write new value to the configuration file."
                                     " Please make sure no other applications are interacting with the configuration "
                                     "file and that \"config.ini\" is located in the folder of the application.")

                # Application is running in debugging mode
                if config_var['RUN-MODE']['run_mode'] == "2":
                    print("\nError: Failed to write new value to the configuration file. Please make sure no other "
                          "applications are interacting with the configuration file and that \"config.ini\" is located "
                          "in the folder of the application.")

        # The variable that shows the current run-mode of the application
        # It is used by the radiobuttons in the filemenu
        self.gui_menu_var = StringVar(self, config_var['RUN-MODE']['run_mode'])
        
        """Declaring the variables the GUI will use"""
        self.menubar = Menu()  # The file menu where the user can specify global settings for the application
        self.filemenu = Menu(self.menubar, tearoff=0)  # Submenu for the file menu
        self.runmode_menu = Menu(self.filemenu, tearoff=0)  # Submenu showing the current run-mode of the application
        
        self.folder_frame = Frame()  # The frame that will display the current media folder

        # The value that stores the current media folder's path as a string
        self.var = StringVar(self, "Please choose the folder where you'd like to store your media:")

        # The label that will display the current media folder
        self.media_folder_label = Label(self.folder_frame, textvariable=self.var)

        # This button will prompt the user to select a media folder
        self.folder_button = Button(self.folder_frame, text="Browse...",
                                    command=lambda: folder_selector(None, self))

        # The button that allows the user to change the currently selected media folder
        self.change_folder_button = ttk.Button(self.folder_frame, text="Change...",
                                               command=lambda: folder_selector(None, self))

        # The frame that will display all the media content available inside the media folder
        self.media_frame = Frame()
        self.canvas = Canvas()

        self.path_frame_parent = Frame(self.media_frame, relief=GROOVE, width=500, height=100, bd=1)

        # Variables related to the search frame of the application
        self.search_frame = Frame()

        self.back_image = PhotoImage(file="Resources/Icons/Back Icon #2.png")
        self.back_button = Button(self.search_frame, image=self.back_image, bg="#ffffff", command=self.display_media)

        self.search_entry = ttk.Entry(self.search_frame, width=50)
        self.search_button = ttk.Button(self.search_frame, text="Search",
                                        command=lambda entry=self.search_entry: self.search(self.search_entry))
        # self.advanced_search_button = ttk.Button(self.search_frame, text="Advanced Search...")

        self.header = Label(self.media_frame, text="Available media:")

        # This label will display when the user attempts to add an already-existent media file
        self.already_exists = Label(self.folder_frame, text="")

        self.button_frame = Frame()

        # The button that allows the user to add media files from other sources
        self.add_music_button = ttk.Button(self.button_frame, text="Add Media...", command=self.add_media_dialog)

        # Savelist-related variables
        self.create_savelist_button = ttk.Button(self.button_frame, text="Create Savelist...",
                                                 command=self.create_savelist)

        self.quit_button = ttk.Button(self.button_frame, text="Exit", command=self.destroy)

        self.archive_name = StringVar()
        self.archive_name.set("")

        # We are storing the length of the longest item in the media list in order to be able to modify the size of the
        # scrollable area (if necessary).
        self.longest_item_length = 0

        self.library_items = []  # The array storing info for every media file (name, buttons, metadata etc.)

        self.process_widgets()

        self.load_interface()

        self.lift()

        print("Graphical user interface loaded.")

    def process_widgets(self):
        """
            Processes the widgets declared in the initialization method of the class.

            :return: None
        """

        self.runmode_menu.add_radiobutton(label="Graphical User Interface", value=0, variable=self.gui_menu_var,
                                          command=self.disable_debugging_mode)
        self.runmode_menu.add_radiobutton(label="Command Line Interface", value=1, variable=self.gui_menu_var,
                                          command=lambda gui=self: load_cli(self))
        self.runmode_menu.add_radiobutton(label="Debugging Mode (GUI + CLI)", value=2, variable=self.gui_menu_var,
                                          command=self.enable_debugging_mode)

        # Placing all the submenus
        self.filemenu.add_cascade(label="Run Mode", menu=self.runmode_menu)
        self.menubar.add_cascade(label="File", menu=self.filemenu)

        self.config(menu=self.menubar)  # Indicating that the "menubar" variable is the filemenu of the application

        self.folder_frame.pack()

        # self.folder_locator.pack(side=LEFT, padx=10, pady=10)

        self.media_folder_label.pack(side=LEFT, padx=10, pady=10)

        self.folder_button.pack(side=LEFT)

        self.path_frame_parent.pack(side=LEFT)

        self.search_frame.pack()

        self.search_frame.pack()
        self.search_entry.grid(row=0, column=0, padx=10, pady=20)
        self.search_button.grid(row=0, column=1, padx=5)
        # self.advanced_search_button.grid(row=0, column=2, padx=5)

        self.media_frame.pack()

        self.button_frame.pack()

    def folder_scan(self):
        """
            Scans the currently selected media folder.
            For every media file it finds, it checks if the specified file is indexed to the database.
            If the file is not indexed (eg. it was manually placed by the user in the media folder), the program
            automatically adds it to the database and refreshes the list of available media.
        """

        cursor = connection.cursor()

        # Parsing the entire media folder and scanning each file
        for filename in os.listdir(media_folder):
            full_path = os.path.join(media_folder, filename).replace("\\", "/")

            # Checks if the file is indexed to the database
            cursor.execute("SELECT COUNT(1) FROM media WHERE full_path = \"" + full_path + "\"")
            result = int(str(cursor.fetchone())[1])

            if not result:  # If the file is not indexed, the program automatically adds it to the database
                add_media(full_path, 1, self)

        connection.commit()

        # Resetting GUI-specific variables and counters before refreshing the media list
        self.library_items = []
        self.path_frame_parent.destroy()
        self.display_media()

    def load_interface(self):
        """
            Loads the GUI of the application.

            :return: None
        """

        self.display_media_folder()

        if media_folder != "":
            self.folder_scan()

        self.add_music_button.grid(row=0, column=0, padx=10, pady=20)
        self.create_savelist_button.grid(row=0, column=1, padx=10, pady=20)
        self.quit_button.grid(row=0, column=2, padx=10, pady=20)

    def display_media(self, search_list=None):
        """
            The core of the program's GUI.
            Displays the entire list of media files to the user, or the list containing the search results for a
            particular search query.

            :param search_list: Optional parameter that specifies the list to be displayed, containing search results.

            :return: None
        """

        global config_var  # Using the global variable that reads and modifies the configuration file

        cursor = connection.cursor()

        index = 0  # Using an index to determine the correct row in which every media item needs to be placed

        if media_folder != "":
            self.header.pack(pady=10)

        # Resetting the media frame
        self.library_items = []
        self.path_frame_parent.destroy()
        self.path_frame_parent = Frame(self.media_frame, relief=GROOVE, width=500, height=100, bd=1)
        self.path_frame_parent.pack()

        # The canvas will store every item in the media list
        self.canvas = Canvas(self.path_frame_parent, width=500)
        path_frame_child = Frame(self.canvas, width=500)

        # Adding a scrollbar in case the media list height exceeds the window height
        scrollbar = Scrollbar(self.path_frame_parent, orient="vertical", command=self.canvas.yview)
        self.canvas.configure(yscrollcommand=scrollbar.set)

        self.canvas.create_window((0, 0), window=path_frame_child, anchor='nw')
        scrollbar.pack(side=RIGHT, fill=Y)
        self.canvas.pack(side=LEFT)

        # The variable that stores the length (in characters) of the longest item in the media list
        self.longest_item_length = 0

        if search_list is None:  # No search string was provided; displaying the entire media list
            self.back_button.grid_forget()
            self.search_entry.delete(0, 'end')

            # Parsing the entire database and displaying every record that matches the current media folder
            cursor.execute("SELECT COUNT(*) FROM media")

            number_of_entries = cursor.fetchone()  # This variable will store the amount of records in the database

            for i in range(number_of_entries[0]):  # Parsing every item in the database
                index += 1

                cursor.execute("SELECT full_path FROM media WHERE id = " + str(i + 1))
                entry_path = cursor.fetchone()  # This variable will store the path of the currently selected item

                display_entry = StringVar()
                display_entry.set(os.path.basename(entry_path[0]))

                # This variable will store the name of the media file without showing the extension
                label_entry = StringVar()
                label_entry.set(os.path.splitext(display_entry.get())[0])

                # Checking if the currently selected item from the database is located in the media folder
                if (os.path.dirname(entry_path[0])) == config_var['MEDIA FOLDER']['folder']:
                    # Adding the media item title to the media list
                    cursor.execute("SELECT mode FROM media WHERE id = " + str(i + 1))
                    mode = cursor.fetchone()

                    if int(mode[0]):  # Displaying the media label using its filename
                        self.library_items.append(Label(path_frame_child, textvariable=display_entry))
                        self.library_items[-1].grid(row=index, column=1)

                        current_item_length = len(display_entry.get())
                        if current_item_length > self.longest_item_length:
                            self.longest_item_length = current_item_length

                    else:  # Displaying the media label using its metadata
                        cursor.execute("SELECT artist FROM media WHERE id = " + str(i + 1))
                        artist = cursor.fetchone()
                        cursor.execute("SELECT title FROM media WHERE id = " + str(i + 1))
                        title = cursor.fetchone()

                        display_label = StringVar()
                        display_label.set(artist[0] + " - " + title[0])

                        self.library_items.append(Label(path_frame_child, textvariable=display_label))
                        self.library_items[-1].grid(row=index, column=1)

                        current_item_length = len(display_label.get())
                        if current_item_length > self.longest_item_length:
                            self.longest_item_length = current_item_length

                    # Adding the play button specific to the current media item
                    self.library_items.append(Button(path_frame_child, text="Play",
                                                     command=lambda file_path=entry_path[0]:
                                                     play_media(file_path, 1, self)))
                    self.library_items[-1].grid(row=index, column=2, padx=10, pady=5)

                    """
                    # Adding the info button specific to the current media item
                    self.library_items.append(Button(path_frame_child, text="Info"))
                    self.library_items[-1].grid(row=index, column=3, padx=10, pady=5)
                    """

                    # Adding the configuration button specific to the current media item
                    self.library_items.append(Button(path_frame_child, text="Configure",
                                                     command=lambda media_title=label_entry.get(),
                                                     file_path=entry_path[0]:
                                                     self.configure_media(media_title, file_path)))
                    self.library_items[-1].grid(row=index, column=4, padx=10, pady=5)

                    # Adding the removal button specific to the current media item
                    self.library_items.append(Button(path_frame_child, text="Remove",
                                                     command=lambda media_title=label_entry.get(),
                                                     file_path=entry_path[0]:
                                                     self.remove_media_query(media_title, file_path)))
                    self.library_items[-1].grid(row=index, column=5, padx=10, pady=5)

        else:  # A search string was provided
            for i in search_list:  # Displaying every item in the search results
                index += 1

                display_entry = StringVar()
                display_entry.set(os.path.basename(i[0]))

                # This variable will store the name of the media file without showing the extension
                label_entry = StringVar()
                label_entry.set(os.path.splitext(display_entry.get())[0])

                # Checking if the currently selected item from the database is located in the media folder
                if (os.path.dirname(i[0])) == config_var['MEDIA FOLDER']['folder']:

                    # Adding the media item title to the media list
                    cursor.execute("SELECT mode FROM media WHERE full_path = " + "\"" + i[0] + "\"")
                    mode = cursor.fetchone()

                    if int(mode[0]):  # Displaying the media label using its metadata
                        self.library_items.append(
                            Label(path_frame_child, textvariable=display_entry))
                        self.library_items[-1].grid(row=index, column=1)

                        current_item_length = len(display_entry.get())
                        if current_item_length > self.longest_item_length:
                            self.longest_item_length = current_item_length

                    else:  # Displaying the media label using its filename
                        cursor.execute("SELECT artist FROM media WHERE full_path = " + "\"" + i[0] + "\"")
                        artist = cursor.fetchone()
                        cursor.execute("SELECT title FROM media WHERE full_path = " + "\"" + i[0] + "\"")
                        title = cursor.fetchone()

                        display_label = StringVar()
                        display_label.set(artist[0] + " - " + title[0])

                        self.library_items.append(
                            Label(path_frame_child, textvariable=display_label))
                        self.library_items[-1].grid(row=index, column=1)

                        current_item_length = len(display_label.get())
                        if current_item_length > self.longest_item_length:
                            self.longest_item_length = current_item_length

                    # Adding the play button specific to the current media item
                    self.library_items.append(Button(path_frame_child, text="Play"))
                    self.library_items[-1].grid(row=index, column=2, padx=10, pady=5)

                    """
                    # Adding the info button specific to the current media item
                    self.library_items.append(Button(path_frame_child, text="Info"))
                    self.library_items[-1].grid(row=index, column=3, padx=10, pady=5)
                    """

                    # Adding the configuration button specific to the current media item
                    self.library_items.append(Button(path_frame_child, text="Configure",
                                                     command=lambda media_title=label_entry.get(), file_path=i[0]:
                                                     self.configure_media(media_title, file_path)))
                    self.library_items[-1].grid(row=index, column=4, padx=10, pady=5)

                    # Adding the removal button specific to the current media item
                    self.library_items.append(Button(path_frame_child, text="Remove",
                                                     command=lambda media_title=label_entry.get(), file_path=i[0]:
                                                     self.remove_media_query(media_title, file_path)))
                    self.library_items[-1].grid(row=index, column=5, padx=10, pady=5)

        # Updating the width of the scrollable area
        path_frame_child.bind("<Configure>", lambda event, x=self.longest_item_length: self.scroll_function(event, x))

        # Refreshing the add button
        self.add_music_button.destroy()
        self.add_music_button = ttk.Button(self.button_frame, text="Add Media...",
                                           command=self.add_media_dialog)
        self.add_music_button.grid(row=0, column=0, padx=10, pady=20)

        # Refreshing the savelist button
        self.create_savelist_button.destroy()
        self.create_savelist_button = ttk.Button(self.button_frame, text="Create Savelist...",
                                                 command=self.create_savelist)
        self.create_savelist_button.grid(row=0, column=1, padx=10, pady=20)

        cursor.close()

    def search(self, entry):
        """
            Searches the database for the value provided in the search box, then updates the media list to show only
            the media files that match the value given.

            :param entry: The search entry box.
            :return: None
        """

        if entry.get() != "":  # The algorithm only needs to run if the user has entered a search query

            cursor = connection.cursor()

            # Looking up the search entry in each of the database's columns
            cursor.execute("SELECT full_path FROM media WHERE INSTR(title, " + "\"" + entry.get() + "\"" +
                           ") > 0 OR INSTR(artist, " + "\"" + entry.get() + "\"" + ") > 0 OR INSTR(album, " + "\"" +
                           entry.get() + "\"" + ") > 0 OR INSTR(release_date, " + "\"" + entry.get() + "\"" + ") > 0" +
                           " OR INSTR(tags, " + "\"" + entry.get() + "\"" + ") > 0")

            files = cursor.fetchall()

            # Packing the "Back" button, which quits the searching session
            self.back_button.grid(row=0, column=0, padx=5)
            self.search_entry.grid(row=0, column=1, padx=10, pady=20)
            self.search_button.grid(row=0, column=2, padx=5)
            # self.advanced_search_button.grid(row=0, column=3, padx=5)

            self.display_media(files)  # Displaying the media list containing only the search results

        else:  # The user has attempted a search on an empty string; displaying the entire media list instead
            self.display_media()

    def scroll_function(self, _, longest_item_length):

        """
            Dictates the specifications of the scrollable area.

            :return: None
        """

        # The width of the scrollable area is calculated as follows:
        # - we assume that every ASCII character is 7-pixels wide
        # - the width of the buttons appended to each media file is around 250 pixels
        # The total width is calculated by multiplying the width of the longest media item by 7, adding the width of
        # the buttons to the result
        self.canvas.configure(scrollregion=self.canvas.bbox("all"), width=longest_item_length * 7 + 250, height=200)
        
    def display_media_folder(self):
        """
            This method makes the media folder label display the correct folder.

            :return: None
        """

        global media_folder
        global config_var

        # Updating the value of the variable storing the path to the media folder
        media_folder = config_var['MEDIA FOLDER']['folder']

        if media_folder != "":  # Checking if the user has previously selected a media folder
            # self.folder_locator.pack_forget()
            self.folder_button.pack_forget()
            self.change_folder_button.pack(side=LEFT, padx=(0, 10))

            # Updating the value of the variable that the media folder label will use
            self.var.set("Media folder: " + media_folder)

    def configure_media(self, label_entry, file_path):
        """
            Opens a window that allows the user to modify song metadata (such as title, artist, release date etc.)
            It also allows the user to specify whether the media file should be displayed using the provided metadata
            or based on the name of the file.

            Note: By default, every record added to the database will have its mode set to '0' (meaning the application
            will display media based on its metadata).

            :param label_entry: Specifies the name of the media item (used for naming the newly created window).
            :param file_path: Specifies the path of the file (used for identifying the correct entry in the database).
            :return: None
        """

        config_window = Toplevel()  # A new window will spawn, allowing the user to modify media metadata
        config_window.title(label_entry)  # Naming the window in correlation with the media file it alters

        var = StringVar(config_window, "0")  # The variable that specifies the mode in which the media file is displayed

        # The frame containing the required radiobuttons for specifying the mode in which the media file is displayed
        radiobutton_frame = Frame(config_window)
        radiobutton_frame.grid()

        metadata_frame = Frame(config_window)
        filename_frame = Frame(config_window)

        # Depending on the selected mode, the contents of the window will change
        mode1_radiobutton = ttk.Radiobutton(radiobutton_frame, text="Display media using metadata tags", variable=var,
                                            value=0, command=lambda x=metadata_frame, y=filename_frame, z=file_path,
                                                                    window=config_window:
                                                                    self.display_metadata_widgets(x, y, z, window))
        mode2_radiobutton = ttk.Radiobutton(radiobutton_frame, text="Display media using filename", variable=var,
                                            value=1, command=lambda x=metadata_frame, y=filename_frame, z=file_path,
                                                                    window=config_window:
                                                                    self.display_filename_widgets(x, y, z, window))

        # Retrieving the current mode of the media file from the database
        cursor = connection.cursor()
        cursor.execute("SELECT mode FROM media WHERE full_path = " + "\"" + file_path + "\"")

        mode = cursor.fetchone()

        if int(mode[0]):  # The media file is displayed using its metadata
            var.set("1")
            self.display_filename_widgets(metadata_frame, filename_frame, file_path, config_window)
        else:  # The media file is displayed using its filename
            var.set("0")
            self.display_metadata_widgets(metadata_frame, filename_frame, file_path, config_window)

        mode1_radiobutton.pack(side=LEFT, padx=10, pady=10)
        mode2_radiobutton.pack(padx=10, pady=10)

        config_window.mainloop()

    def remove_media_query(self, media_title, file_path):
        """
            Prompts the user to remove the selected media file from the list.

            :param media_title: The title of the media file to be removed.
            :param file_path: The path of the media file to be removed.
            :return: None
        """

        remove_window = Toplevel()  # A new window will spawn, allowing the user to remove selected media
        remove_window.title("Remove \"" + media_title + "\"?")
        # The user is not allowed to interact with the root window while the remove window is opened
        remove_window.grab_set()

        remove_label = Label(remove_window, text="Are you sure you want to remove \"" + media_title +
                                                 "\" from the media folder?")
        remove_label.pack(padx=10, pady=10)

        button_frame = Frame(remove_window)
        button_frame.pack()

        remove_button = Button(button_frame, text="Remove media", command=lambda x=file_path, y=remove_window:
                               remove_media(x, y, self))
        remove_button.grid(row=0, column=0, padx=10, pady=10)

        cancel_button = Button(button_frame, text="Cancel", command=remove_window.destroy)
        cancel_button.grid(row=0, column=1, padx=10, pady=10)

        remove_window.mainloop()

    def display_metadata_widgets(self, metadata_frame, filename_frame, media_path, window):
        """
            Displays the body of the configuration window. In this mode, the contents of the body will not allow the
            user to modify the name of the file.

            :param metadata_frame: The required frame if the media's current mode is set to '0'.
            :param filename_frame: The required frame if the media's current mode is set to '1'.
            :param media_path: The path of the media file.
            :param window: The current window in which changes are being applied.
            :return: None
        """

        filename_frame.grid_forget()  # Removing the frame required for mode '1'
        metadata_frame.grid(row=1, column=0)  # Adding the frame required for mode '0'

        # Gathering all metadata related to the media file
        cursor = connection.cursor()

        cursor.execute("SELECT title FROM media WHERE full_path = " + "\"" + media_path + "\"")
        song_title_sql = cursor.fetchone()

        cursor.execute("SELECT artist FROM media WHERE full_path = " + "\"" + media_path + "\"")
        song_artist_sql = cursor.fetchone()

        cursor.execute("SELECT album FROM media WHERE full_path = " + "\"" + media_path + "\"")
        song_album_sql = cursor.fetchone()

        cursor.execute("SELECT release_date FROM media WHERE full_path = " + "\"" + media_path + "\"")
        release_date_sql = cursor.fetchone()

        cursor.execute("SELECT tags FROM media WHERE full_path = " + "\"" + media_path + "\"")
        tags_sql = cursor.fetchone()

        # Loading the GUI of the metadata frame
        path_entry = ttk.Entry(metadata_frame)
        path_entry.insert(0, os.path.basename(media_path))

        title_label = ttk.Label(metadata_frame, text="Song title:")
        title_entry = ttk.Entry(metadata_frame, width=30)
        title_entry.insert(0, song_title_sql[0])
        title_entry.focus_set()

        artist_label = ttk.Label(metadata_frame, text="Artist:")
        artist_entry = ttk.Entry(metadata_frame, width=30)
        artist_entry.insert(0, song_artist_sql[0])

        album_label = ttk.Label(metadata_frame, text="Album:")
        album_entry = ttk.Entry(metadata_frame, width=30)
        album_entry.insert(0, song_album_sql[0])

        release_date_label = ttk.Label(metadata_frame, text="Release date:")
        release_date_entry = ttk.Entry(metadata_frame, width=30)
        release_date_entry.insert(0, release_date_sql[0])

        tags_label = ttk.Label(metadata_frame, text="Tags:")
        tags_entry = ttk.Entry(metadata_frame, width=30)
        tags_entry.insert(0, tags_sql[0])

        # Displaying the GUI of the metadata frame
        title_label.grid(row=0, column=0, pady=5)
        title_entry.grid(row=0, column=1, pady=5)
        artist_label.grid(row=1, column=0, pady=5)
        artist_entry.grid(row=1, column=1, pady=5)
        album_label.grid(row=2, column=0, pady=5)
        album_entry.grid(row=2, column=1, pady=5)
        release_date_label.grid(row=3, column=0, pady=5)
        release_date_entry.grid(row=3, column=1, pady=5)
        tags_label.grid(row=4, column=0, pady=5)
        tags_entry.grid(row=4, column=1, pady=5)

        # The button that applies all changes and saves them to the database
        submit_button = ttk.Button(metadata_frame, text="Save",
                                   command=lambda path_value=path_entry, title_value=title_entry,
                                   artist_value=artist_entry, album_value=album_entry,
                                   release_date_value=release_date_entry, tags_value=tags_entry, x_window=window:
                                   self.update_entry(path_value, 0, title_value, artist_value, album_value,
                                                     release_date_value, tags_value, 0, media_path, x_window))

        # The button that discards all changes
        cancel_button = ttk.Button(metadata_frame, text="Cancel", command=window.destroy)

        submit_button.grid(row=5, column=0, padx=10, pady=10)
        cancel_button.grid(row=5, column=1, padx=10, pady=10)

    def display_filename_widgets(self, metadata_frame, filename_frame, media_path, window):
        """
            Displays the body of the configuration window. In this mode, the contents of the body will allow the user to
            modify the name of the file.

            :param metadata_frame: The required frame if the media's current mode is set to '0'.
            :param filename_frame: The required frame if the media's current mode is set to '1'.
            :param media_path: The path of the media file.
            :param window: The current window in which changes are being applied.
            :return: None
        """

        metadata_frame.grid_forget()  # Removing the frame required for mode '0'
        filename_frame.grid(row=1, column=0)  # Adding the frame required for mode '1'

        # Gathering all metadata related to the media file
        cursor = connection.cursor()

        cursor.execute("SELECT title FROM media WHERE full_path = " + "\"" + media_path + "\"")
        song_title_sql = cursor.fetchone()

        cursor.execute("SELECT artist FROM media WHERE full_path = " + "\"" + media_path + "\"")
        song_artist_sql = cursor.fetchone()

        cursor.execute("SELECT album FROM media WHERE full_path = " + "\"" + media_path + "\"")
        song_album_sql = cursor.fetchone()

        cursor.execute("SELECT release_date FROM media WHERE full_path = " + "\"" + media_path + "\"")
        release_date_sql = cursor.fetchone()

        cursor.execute("SELECT tags FROM media WHERE full_path = " + "\"" + media_path + "\"")
        tags_sql = cursor.fetchone()

        character_count = len(os.path.basename(media_path))

        # Loading the GUI of the filename frame
        path_label = ttk.Label(filename_frame, text="Song filename:")
        path_entry = ttk.Entry(filename_frame, width=character_count)
        path_entry.insert(0, os.path.basename(media_path))
        path_entry.focus_set()

        title_label = ttk.Label(filename_frame, text="Song title:")
        title_entry = ttk.Entry(filename_frame, width=30)
        title_entry.insert(0, song_title_sql[0])

        artist_label = ttk.Label(filename_frame, text="Artist:")
        artist_entry = ttk.Entry(filename_frame, width=30)
        artist_entry.insert(0, song_artist_sql[0])

        album_label = ttk.Label(filename_frame, text="Album:")
        album_entry = ttk.Entry(filename_frame, width=30)
        album_entry.insert(0, song_album_sql[0])

        release_date_label = ttk.Label(filename_frame, text="Release date:")
        release_date_entry = ttk.Entry(filename_frame, width=30)
        release_date_entry.insert(0, release_date_sql[0])

        tags_label = ttk.Label(filename_frame, text="Tags:")
        tags_entry = ttk.Entry(filename_frame, width=30)
        tags_entry.insert(0, tags_sql[0])

        # Displaying the GUI of the filename frame
        path_label.grid(row=0, column=0, pady=5)
        path_entry.grid(row=0, column=1, pady=5)
        title_label.grid(row=1, column=0, pady=5)
        title_entry.grid(row=1, column=1, pady=5)
        artist_label.grid(row=2, column=0, pady=5)
        artist_entry.grid(row=2, column=1, pady=5)
        album_label.grid(row=3, column=0, pady=5)
        album_entry.grid(row=3, column=1, pady=5)
        release_date_label.grid(row=4, column=0, pady=5)
        release_date_entry.grid(row=4, column=1, pady=5)
        tags_label.grid(row=5, column=0, pady=5)
        tags_entry.grid(row=5, column=1, pady=5)

        # The button that applies all changes and saves them to the database
        submit_button = ttk.Button(filename_frame, text="Save",
                                   command=lambda path_value=path_entry, title_value=title_entry,
                                   artist_value=artist_entry, album_value=album_entry,
                                   release_date_value=release_date_entry, tags_value=tags_entry, x_window=window:
                                   self.update_entry(path_value, 1, title_value, artist_value, album_value,
                                                     release_date_value, tags_value, 1, media_path, x_window))

        # The button that discards all changes
        cancel_button = ttk.Button(filename_frame, text="Cancel", command=window.destroy)

        submit_button.grid(row=6, column=0, padx=10, pady=10)
        cancel_button.grid(row=6, column=1, padx=10, pady=10)

    def update_entry(self, path_value, run_mode, title_value, artist_value, album_value, release_date_value, tags_value,
                     mode, media_path, window):
        """
            Modifies the specified record of the database with respect to the values passed as arguments.

            :param path_value: The new path of the media file.
            :param run_mode: Specifies whether the algorithm can rename the file inside the media folder.
            :param title_value: The new title of the media file.
            :param artist_value: The new artist of the media file.
            :param album_value: The new album of the media file.
            :param release_date_value: The new release date of the media file.
            :param tags_value: The new tags of the media file.
            :param mode: The mode of the media file.
            :param media_path: The (new) path of the media file.
            :param window: The window which will need to close after database update.

            :return: True: The database was successfully updated.
            :return: False: Could not write changes to the database.
        """

        new_path = ""  # The variable storing the new path for the media file (if necessary)

        if run_mode:  # The algorithm will rename the file inside the media folder as specified by the user
            new_path = os.path.join(os.path.dirname(media_path), path_value.get())  # New filename
            os.rename(media_path, new_path)

        # We will use the "media_path" argument of the method to determine which database record needs to be updated
        cursor = connection.cursor()

        try:
            cursor.execute("UPDATE media SET title = " + "\"" + title_value.get() + "\"" + ", artist = " + "\"" +
                           artist_value.get() + "\"" + ", album = " + "\"" + album_value.get() + "\"" +
                           ", release_date = " + "\"" + release_date_value.get() + "\"" + ", tags = " + "\"" +
                           tags_value.get() + "\"" + ", mode = " + str(mode) + " WHERE full_path = " + "\""
                           + media_path + "\"")
            if run_mode:  # Updating the full path in the database as well
                cursor.execute("UPDATE media SET full_path = " + "\"" + new_path + "\"" + " WHERE full_path = " + "\"" +
                               media_path + "\"")

        except Error:
            messagebox.showerror("Database is locked", "Could not write changes to the database. Make sure no other "
                                 "application is currently modifying the database.")

            return False

        connection.commit()
        cursor.close()

        window.destroy()  # Unloading the configuration window

        # Reloading the media list of the root window
        self.library_items = []
        self.path_frame_parent.destroy()
        self.display_media()

        return True

    def add_media_dialog(self):
        """
            Prompts the user to select a media file to be added to the media list.

            :return: None
        """

        file = filedialog.askopenfilename()

        if add_media(file, 0, self):  # Checking if the process of adding the media file was successful

            if file:  # Checking whether the user has aborted the operation
                # Getting the path of the file with respect to the current media folder (since the "file" variable
                # points to the location of the source file)
                full_path = os.path.join(media_folder, os.path.basename(file)).replace("\\", "/")

                # Whenever a media item is added, the user is automatically prompted to configure its metadata
                self.configure_media(os.path.basename(file), full_path)

    def create_savelist(self):
        """
            Displays a window that prompts the user to create a custom savelist based on certain criteria.

            :return: None
        """

        savelist_window = Toplevel()  # A new window will spawn, allowing the user to create a custom Savelist
        savelist_window.title("Create Savelist...")

        # Blocks the user from interacting with the root window while the savelist window is active
        savelist_window.grab_set()

        savelist_label = Label(savelist_window, text="Create a custom Savelist based on certain criteria.\n "
                                                     "Leave any field empty to ignore that criterion.\n "
                                                     "The resulted Savelist will be generated inside the media folder.")
        savelist_label.pack(padx=10, pady=10)

        savelist_frame = Frame(savelist_window)
        savelist_frame.pack()

        title_contains_label = Label(savelist_frame, text="Title contains:")
        title_contains_label.grid(row=0, column=0, padx=10, pady=10)

        title_contains_entry = ttk.Entry(savelist_frame)
        title_contains_entry.grid(row=0, column=1)

        artist_name_label = Label(savelist_frame, text="Artist name:")
        artist_name_label.grid(row=1, column=0, padx=10, pady=10)

        artist_name_entry = ttk.Entry(savelist_frame)
        artist_name_entry.grid(row=1, column=1)

        album_name_label = Label(savelist_frame, text="Album name:")
        album_name_label.grid(row=2, column=0, padx=10, pady=10)

        album_name_entry = ttk.Entry(savelist_frame)
        album_name_entry.grid(row=2, column=1)

        release_year_label = Label(savelist_frame, text="Release year:")
        release_year_label.grid(row=3, column=0, padx=10, pady=10)

        release_year_entry = ttk.Entry(savelist_frame)
        release_year_entry.grid(row=3, column=1)

        tags_label = Label(savelist_frame, text="Tags:")
        tags_label.grid(row=4, column=0, padx=10, pady=10)

        tags_entry = ttk.Entry(savelist_frame)
        tags_entry.grid(row=4, column=1)

        archive_name_label = Label(savelist_frame, text="Name of the generated archive:")
        archive_name_label.grid(row=5, column=0, padx=10, pady=10)

        archive_name_entry = ttk.Entry(savelist_frame, textvariable=self.archive_name)
        archive_name_entry.grid(row=5, column=1)

        button_frame = Frame(savelist_window)
        button_frame.pack()

        # The button that attempts to create the archive based on the specified parameters
        # By default, the button is disabled as long as the "Archive Name" entry is left blank
        generate_button = ttk.Button(button_frame, text="Generate Savelist", state="disabled", command=lambda
                                     title_value=title_contains_entry, artist_value=artist_name_entry,
                                     album_value=album_name_entry, release_year_value=release_year_entry,
                                     tags_value=tags_entry, archive_value=archive_name_entry, x_window=savelist_window:
                                     self.generate_savelist(title_value, artist_value, album_value, release_year_value,
                                                            tags_value, archive_value, x_window))
        generate_button.grid(row=6, column=0, padx=10, pady=10)

        # The partial method that checks if the "Archive Name" entry is filled
        on_enter_trace = partial(self.on_enter_trace, generate_button)
        self.archive_name.trace("w", on_enter_trace)

        # The button that cancels the Savelist action
        cancel_button = ttk.Button(button_frame, text="Cancel", command=savelist_window.destroy)
        cancel_button.grid(row=6, column=1, padx=10, pady=10)

        savelist_window.mainloop()

    def on_enter_trace(self, button, *_):
        """
            This function scans the archive name entry. If the entry is empty, the user cannot proceed to create a
            Savelist archive.

            :param button: The button whose state will change depending on the completion of the archive name entry.
            :param _: Partial methods send multiple variables as parameters. We do not need them for the purpose of this
            method.

            :return: None
        """

        if self.archive_name.get() == "":  # The archive name entry is empty
            button.configure(state="disabled")
        else:  # The archive name entry is filled
            button.configure(state="enabled")

    def generate_savelist(self, title, artist, album, release_year, tags, archive, window):
        """
            Creates a .zip file using the contents specified by the user in the entry fields. The .zip file is placed
            in the media folder. The algorithm attempts to create the intersection of each SQL result from the provided
            tags, in order for the final resulted list to contain only the media files that match every criterion
            specified by the user.

            :param title: The contents of the title entry.
            :param artist: The contents of the artist entry.
            :param album: The contents of the album entry.
            :param release_year: The contents of the release year entry.
            :param tags: The contents of the tags entry.
            :param archive: The contents of the archive entry.
            :param window: The window which will need to close after archive creation.

            :return: None
        """

        cursor = connection.cursor()

        # The arrays storing the results of the SQL entries for each of the entries' contents
        valid_title_files = []
        valid_artist_files = []
        valid_album_files = []
        valid_release_year_files = []
        valid_tags_files = []

        # Creating the archive file using the name provided in the archive entry
        with zipfile.ZipFile(media_folder + "/" + archive.get() + '.zip', 'w') as savelist_zip:

            if title.get() != "":  # The user has specified a custom criterion for the title
                cursor.execute("SELECT full_path FROM media WHERE INSTR(title, " + "\"" + title.get() + "\"" +
                               ") > 0")

                for i in cursor.fetchall():  # Updating the corresponding list using the cursor result
                    valid_title_files.append(i[0])

            if artist.get() != "":  # The user has specified a custom criterion for the artist
                cursor.execute("SELECT full_path FROM media WHERE INSTR(artist, " + "\"" + artist.get() + "\"" +
                               ") > 0")

                for i in cursor.fetchall():  # Updating the corresponding list using the cursor result
                    valid_artist_files.append(i[0])

            if album.get() != "":  # The user has specified a custom criterion for the album
                cursor.execute("SELECT full_path FROM media WHERE INSTR(album, " + "\"" + album.get() + "\"" +
                               ") > 0")

                for i in cursor.fetchall():  # Updating the corresponding list using the cursor result
                    valid_album_files.append(i[0])

            if release_year.get() != "":  # The user has specified a custom criterion for the release year
                cursor.execute("SELECT full_path FROM media WHERE INSTR(release_date, " + "\"" + release_year.get() +
                               "\") > 0")

                for i in cursor.fetchall():  # Updating the corresponding list using the cursor result
                    valid_release_year_files.append(i[0])

            if tags.get() != "":  # The user has specified a custom criterion for the tags
                cursor.execute("SELECT full_path FROM media WHERE INSTR(" + "\"" + tags.get() + "\"" +
                               ", tags) > 0")

                for i in cursor.fetchall():  # Updating the corresponding list using the cursor result
                    valid_tags_files.append(i[0])

            # We are now performing intersection operation for each of the lists in order to add to the archive only
            # the files that match every criterion passed by the user
            files = intersection(intersection(intersection(intersection(valid_title_files, valid_artist_files),
                                 valid_album_files), valid_release_year_files), valid_tags_files)

            for index in files:  # Writing the suitable files to the archive
                savelist_zip.write(index, os.path.basename(index))

        savelist_zip.close()  # Closing the archive

        self.archive_name.set("")  # Resetting the archive name variable for further use

        window.destroy()  # Closing the Savelist window

    @staticmethod
    def enable_debugging_mode():
        """
            Updates the configuration file to indicate the application's methods that debugging mode is now enabled.

            :return: None
        """

        global config_var  # Using the global variable that reads and modifies the configuration file

        config_var.set('RUN-MODE', 'run_mode', "2")

        try:
            with open('config.ini', 'w') as configfile_gui:
                config_var.write(configfile_gui)  # Writing the changes to the configuration file
                configfile_gui.close()

        except IOError:
            messagebox.showerror("Writing to file failed", "Failed to write new value to the configuration file."
                                 " Please make sure no other applications are interacting with the configuration "
                                 "file and that \"config.ini\" is located in the folder of the application.")

            # Application is running in debugging mode
            if config_var['RUN-MODE']['run_mode'] == "2":
                print("\nError: Failed to write new value to the configuration file. Please make sure no other "
                      "applications are interacting with the configuration file and that \"config.ini\" is located "
                      "in the folder of the application.")

    @staticmethod
    def disable_debugging_mode():
        """
            Updates the configuration file to indicate the application's methods that debugging mode is now disabled.

            :return: None
        """

        global config_var  # Using the global variable that reads and modifies the configuration file

        config_var.set('RUN-MODE', 'run_mode', "0")

        try:
            with open('config.ini', 'w') as configfile_gui:
                config_var.write(configfile_gui)  # Writing the changes to the configuration file
                configfile_gui.close()

        except IOError:
            messagebox.showerror("Writing to file failed", "Failed to write new value to the configuration file."
                                 " Please make sure no other applications are interacting with the configuration "
                                 "file and that \"config.ini\" is located in the folder of the application.")

            # Application is running in debugging mode
            if config_var['RUN-MODE']['run_mode'] == "2":
                print("\nError: Failed to write new value to the configuration file. Please make sure no other "
                      "applications are interacting with the configuration file and that \"config.ini\" is located "
                      "in the folder of the application.")


class SongStorageCLI:  # The class responsible for running the application in the console
    def __init__(self, run_mode):
        """
            Initialization method of the class. Checks whether application is running in loop mode or a single
            iteration.

            :return: None
        """

        global config_var  # Using the global variable that reads and modifies the configuration file

        self.run_mode = run_mode

        if self.run_mode:  # The application is running in loop mode
            config_var.set('RUN-MODE', 'run_mode', "1")

            try:
                with open('config.ini', 'w') as configfile_cli:
                    config_var.write(configfile_cli)  # Writing the changes to the configuration file
                    configfile_cli.close()

            except IOError:
                print("\nError: Failed to write new value to the configuration file. Please make sure no other "
                      "applications are interacting with the configuration file and that \"config.ini\" is located "
                      "in the folder of the application.")

            print("\nSong Storage\n")
            print("Please type a command.\nType \"help\" for a list of commands.\nType \"quit\" to exit the program. "
                  "Type \"load_gui\" to go back to the graphical user interface version.")

            while self.run_mode:  # The application will continue to listen for user commands
                command = input("\nInsert command: ")
                self.process_command(command.lower())

        else:  # The user is running the application using command line arguments; no additional iterations required
            if sys.argv[1].lower() == "add_song":
                add_media(sys.argv[2], 0)

            elif sys.argv[1].lower() == "delete_song":
                remove_media(sys.argv[2])

            elif sys.argv[1].lower() == "list_media":
                self.display_media_cli()

            elif sys.argv[1].lower() == "media_folder":
                self.configure_media_folder(sys.argv)

            elif sys.argv[1].lower() == "modify_data":
                self.configure_media(sys.argv[2])

            elif sys.argv[1].lower() == "create_save_list":
                self.generate_savelist_cli(sys.argv)

            elif sys.argv[1].lower() == "search":
                self.search_cli(sys.argv)

            elif sys.argv[1].lower() == "play":
                play_media(sys.argv[2], 0)

            elif sys.argv[1].lower() == "load_gui":
                load_gui()

            elif sys.argv[1].lower() == "help":
                self.display_help_cli()

            else:
                print("\nUnrecognized command \"" + sys.argv[1] + "\".\n"
                      "Use command \"Help\" for a list of available commands.")

    def process_command(self, command):
        """
            Processes and executes the command specified by the user.

            :param command: The command to be executed.

            :return: None
        """

        tokenized_command = command.split()  # Splitting the command and the arguments into separate list elements

        # In order to save a lot of code writing, we are making the command appear the same as the ones from single
        # iteration modes. This way, the same method that handles the commands in single iteration mode is now able
        # to process commands from the looped run mode as well.
        sys_argv_emulation = tokenized_command.copy()
        sys_argv_emulation.insert(0, "filler argument")

        if tokenized_command[0] == "add_song":
            add_media(tokenized_command[1], 0)

        elif tokenized_command[0] == "delete_song":
            remove_media(tokenized_command[1])

        elif tokenized_command[0] == "list_media":
            self.display_media_cli()

        elif tokenized_command[0] == "media_folder":
            self.configure_media_folder(sys_argv_emulation)

        elif tokenized_command[0] == "modify_data":
            self.configure_media(tokenized_command[1])

        elif tokenized_command[0] == "create_save_list":
            self.generate_savelist_cli(sys_argv_emulation)

        elif tokenized_command[0] == "search":
            self.search_cli(sys_argv_emulation)

        elif tokenized_command[0] == "play":
            play_media(tokenized_command[1], 1)

        elif tokenized_command[0] == "load_gui":
            self.run_mode = 0
            load_gui()

        elif tokenized_command[0] == "help":
            self.display_help_cli()

        elif tokenized_command[0] == "quit":
            sys.exit()

        else:
            print("\nUnrecognized command \"" + tokenized_command[0] + "\".\n"
                  "Use command \"Help\" for a list of available commands.")

    @staticmethod
    def display_help_cli():
        """
            Displays a help message containing all commands of the application.

            :return: None
        """

        print("\nAdd_song [path to song] - Adds the specified media file to the media folder (only .mp3 and .wav files "
              "are supported).\n")

        print("Delete_song [ID of the song | name of the media file] - Deletes the specified media file from the media "
              + "folder.\n")

        print("List_media - Displays the entire media list located in the media folder.\n")

        print("Media_folder [directory path]* - If no arguments are given, displays the current media folder. " +
              "Otherwise, changes the media folder to the specified directory.\n")

        print("Modify_data [ID of the song | name of the media file] - Allows the user to modify information for the "
              + "specified media file.\n")

        print("Search [(title= | artist= | album= | release_date= | tags=)* + search query] - Searches the database " +
              "for media files matching the search query and displays the results.\n")

        print("Create_save_list [archive name] [(title= | artist= | album= | release_date= | tags=)* + search query] " +
              "- Creates an archive in the media folder containing the media files matching the search query.\n")

        print("Play [ID of the song | name of the media file] - Plays the currently selected media file in the " +
              "background.\n")

        print("Load_gui - Loads the graphical user interface of the application.\n")

        print("Help - Displays this help message.\n")

        print("Quit - Exits the applicatin.\n")

    @staticmethod
    def configure_media(file):
        """
            This is the method used by the CLI for modifying media metadata.

            :param file: The media file to be altered.
            :return: None
        """

        global option  # Using the global variable that specifies user choice (typically "Yes" or "No" choices)
        cursor = connection.cursor()

        if file.isnumeric():  # The user has attempted to configure the media file based on its ID in the database
            cursor.execute("SELECT full_path FROM media WHERE id = " + file)

            full_path_cursor = cursor.fetchone()

            if full_path_cursor is None:  # The system couldn't find the specified ID
                print("\nError: The specified ID does not exist in the database.")
                return

            full_path = full_path_cursor[0]

        else:  # The user is either using the GUI or has provided the filename as parameter
            full_path = os.path.join(media_folder, os.path.basename(file)).replace("\\", "/")

            if not path.exists(full_path):  # (CLI-only) The user has provided an invalid filename
                print("\nError: The specified media file does not exist.")
                return

        # Processing the media file in the database
        cursor.execute("SELECT id FROM media WHERE full_path = " + "\"" + full_path + "\"")

        entry_id = cursor.fetchone()

        # For each column in the database, we will present the user the current value for the media item and we will
        # ask them if they want to update this value.
        print("\nFilename: " + ntpath.basename(full_path) + "\nRename file? (Y/N)")  # The current full_path value

        option = input()  # Getting user response

        if option.lower() == "y":  # The user has responded affirmatively
            filename = input("\nNew filename: ")  # Inquiring the user about the new filename

            new_path = os.path.join(os.path.dirname(full_path), filename).replace("\\", "/")  # New filename
            os.rename(full_path, new_path)  # Renaming the file

            cursor.execute("UPDATE media SET full_path = " + "\"" + new_path + "\"" + " WHERE full_path = " + "\"" +
                           full_path + "\"")
            connection.commit()  # Writing the changes to the database

            print("\nFile renamed successfully.")

        cursor.execute("SELECT title FROM media WHERE id = " + str(entry_id[0]))
        song_title = cursor.fetchone()

        print("\nSong title: " + song_title[0] + "\nRename song? (Y/N)")  # The current title value

        option = input()  # Getting user response

        if option.lower() == "y":  # The user has responded affirmatively
            new_song_title = input("\nNew song title: ")  # Inquiring the user about the new song title

            cursor.execute(
                "UPDATE media SET title = " + "\"" + new_song_title + "\"" + " WHERE id = " + str(entry_id[0]))
            connection.commit()  # Writing the changes to the database

            print("\nSong title updated successfully.")

        cursor.execute("SELECT artist FROM media WHERE id = " + str(entry_id[0]))
        song_artist = cursor.fetchone()

        print("\nArtist: " + song_artist[0] + "\nRename artist? (Y/N)")  # The current artist value

        option = input()  # Getting user response

        if option.lower() == "y":  # The user has responded affirmatively
            new_song_artist = input("\nNew artist: ")  # Inquiring the user about the new artist

            cursor.execute(
                "UPDATE media SET artist = " + "\"" + new_song_artist + "\"" + " WHERE id = " + str(entry_id[0]))
            connection.commit()  # Writing the changes to the database

            print("\nArtist updated successfully.")

        cursor.execute("SELECT album FROM media WHERE id = " + str(entry_id[0]))
        song_album = cursor.fetchone()

        print("\nAlbum: " + song_album[0] + "\nRename album? (Y/N)")  # The current album value

        option = input()  # Getting user response

        if option.lower() == "y":  # The user has responded affirmatively
            new_song_album = input("\nNew album: ")  # Inquiring the user about the new album

            cursor.execute(
                "UPDATE media SET album = " + "\"" + new_song_album + "\"" + " WHERE id = " + str(entry_id[0]))
            connection.commit()  # Writing the changes to the database

            print("\nAlbum updated successfully.")

        cursor.execute("SELECT release_date FROM media WHERE id = " + str(entry_id[0]))
        song_release_date = cursor.fetchone()

        print("\nRelease date: " + song_release_date[
            0] + "\nChange release date? (Y/N)")  # The current release date value

        option = input()  # Getting user response

        if option.lower() == "y":  # The user has responded affirmatively
            new_release_date = input("\nNew release date: ")  # Inquiring the user about the new release date

            cursor.execute("UPDATE media SET release_date = " + "\"" + new_release_date + "\"" + " WHERE id = " +
                           str(entry_id[0]))
            connection.commit()  # Writing the changes to the database

            print("\nSong release date updated successfully.")

        cursor.execute("SELECT tags FROM media WHERE id = " + str(entry_id[0]))
        song_tags = cursor.fetchone()

        print("\nSong tags: " + song_tags[0] + "\nChange tags? (Y/N)")  # The current tags value

        option = input()  # Getting user response

        if option.lower() == "y":  # The user has responded affirmatively
            # Inquiring the user about the new tags
            new_song_tags = input("\nNew song tags (separate tags by using a comma (','), whitespaces are optional): ")

            cursor.execute("UPDATE media SET tags = " + "\"" + new_song_tags + "\"" + " WHERE id = " + str(entry_id[0]))
            connection.commit()  # Writing the changes to the database

            print("\nSong tags updated successfully.")

        print("\nConfiguration completed.")

    @staticmethod
    def display_media_cli():
        """
            Dedicated method for displaying the media list in command-line interfaces. On each line, the output displays
            one item from the media list, followed by its ID in the database. The algorithm only displays media items
            from the current media folder.

            :return: None
        """

        global config_var  # Using the global variable that reads and modifies the configuration file

        cursor = connection.cursor()
        count = 0  # The total amount of items displayed

        # Parsing the entire database and displaying every record that matches the current media folder
        cursor.execute("SELECT COUNT(*) FROM media")

        number_of_entries = cursor.fetchone()  # This variable will store the amount of records in the database

        for i in range(number_of_entries[0]):
            cursor.execute("SELECT full_path FROM media WHERE id = " + str(i + 1))
            entry_path = cursor.fetchone()  # This variable will store the path of the currently selected item

            # Checking if the currently selected item from the database is located in the media folder
            if (os.path.dirname(entry_path[0])) == config_var['MEDIA FOLDER']['folder']:
                print("\n" + os.path.basename(entry_path[0]) + " || ID: " + str(i + 1))
                count += 1

        if not count:  # No items could be found
            print("\nThere are no media files in the media folder.")

        cursor.close()

    @staticmethod
    def generate_savelist_cli(sys_arguments):
        """
            Creates a .zip file using the contents specified by the user in the entry fields. The .zip file is placed
            in the media folder. The algorithm attempts to create the intersection of each SQL result from the provided
            tags, in order for the final resulted list to contain only the media files that match every criterion
            specified by the user.

            :param sys_arguments: Arguments passed at the command line.
            :return: None
        """

        cursor = connection.cursor()

        # The arrays storing the results of the SQL entries for each of the entries' contents
        valid_title_files = []
        valid_artist_files = []
        valid_album_files = []
        valid_release_year_files = []
        valid_tags_files = []

        # Creating the archive file using the name provided in the archive entry
        with zipfile.ZipFile(media_folder + "/" + sys_arguments[2] + '.zip', 'w') as savelist_zip:
            for index in range(len(sys_arguments) - 3):
                if sys_arguments[index + 3].startswith(
                        "title="):  # The user has specified a custom criterion for the title
                    cursor.execute(
                        "SELECT full_path FROM media WHERE INSTR(title, " + "\"" + sys_arguments[index + 3][6:]
                        + "\"" + ") > 0")

                    for i in cursor.fetchall():  # Updating the corresponding list using the cursor result
                        valid_title_files.append(i[0])

                # The user has specified a custom criterion for the artist
                if sys_arguments[index + 3].startswith("artist="):
                    cursor.execute(
                        "SELECT full_path FROM media WHERE INSTR(artist, " + "\"" + sys_arguments[index + 3][7:] + "\""
                        + ") > 0")

                    for i in cursor.fetchall():  # Updating the corresponding list using the cursor result
                        valid_artist_files.append(i[0])

                if sys_arguments[index + 3].startswith(
                        "album="):  # The user has specified a custom criterion for the album
                    cursor.execute(
                        "SELECT full_path FROM media WHERE INSTR(album, " + "\"" + sys_arguments[index + 3][6:] + "\""
                        + ") > 0")

                    for i in cursor.fetchall():  # Updating the corresponding list using the cursor result
                        valid_album_files.append(i[0])

                # The user has specified a custom criterion for the release year
                if sys_arguments[index + 3].startswith("release_year="):
                    cursor.execute(
                        "SELECT full_path FROM media WHERE INSTR(release_date, " + "\"" + sys_arguments[index + 3][13:]
                        + "\") > 0")

                    for i in cursor.fetchall():  # Updating the corresponding list using the cursor result
                        valid_release_year_files.append(i[0])

                # The user has specified a custom criterion for the tags
                if sys_arguments[index + 3].startswith("tags="):
                    tags_list = sys_arguments[index + 3][5:].replace('\"', '').replace(' ', '').split(",")

                    for tag in tags_list:
                        cursor.execute("SELECT full_path FROM media WHERE INSTR(tags, \"" + tag + "\") > 0")

                        for i in cursor.fetchall():  # Updating the corresponding list using the cursor result
                            valid_tags_files.append(i[0])

                # We are now performing intersection operation for each of the lists in order to add to the archive only
                # the files that match every criterion passed by the user
                files = intersection(intersection(intersection(intersection(valid_title_files, valid_artist_files),
                                                               valid_album_files), valid_release_year_files),
                                     valid_tags_files)

                for index2 in files:  # Writing the suitable files to the archive
                    savelist_zip.write(index2, os.path.basename(index2))

        savelist_zip.close()  # Closing the archive

        print("\nArchive created successfully.")

    @staticmethod
    def configure_media_folder(arguments):
        """
            CLI-only method. Either displays the current media folder or changes it to the specified value.

            :param arguments: Arguments passed at the command line. Minimum 1 argument needs to be passed for this
                              method to run. The first argument specifies the name of the command. The 2nd parameter
                              is optional and specifies the location of the new media folder.
            :return: None
        """

        if len(arguments) == 1:  # The user is inquiring about the location of the current media folder
            if media_folder == "":  # No media folder is configured
                print("\nNo media folder selected. "
                      "Use \"media_folder [path to a directory]\" command to set up a media folder.")

            else:  # A media folder exists
                print("\nMedia folder: " + media_folder)

        elif len(arguments) == 2:  # The user is attempting to change the media folder
            folder_selector(arguments[1])

        else:
            return

        if len(arguments) == 2:  # The user is inquiring about the location of the current media folder
            if media_folder == "":  # No media folder is configured
                print("\nNo media folder selected. "
                      "Use \"media_folder [path to a directory]\" command to set up a media folder.")

            else:  # A media folder exists
                print("\nMedia folder: " + media_folder)

        elif len(arguments) == 3:  # The user is attempting to change the media folder
            folder_selector(arguments[2])

    @staticmethod
    def search_cli(sys_arguments):
        """
            Searches the database for the value provided in the search box, then updates the media list to show only
            the media files that match the value given.

            :param sys_arguments: Arguments passed at the command line.
            :return: None
        """

        cursor = connection.cursor()

        # The arrays storing the results of the SQL entries for each of the entries' contents
        valid_title_files = []
        valid_artist_files = []
        valid_album_files = []
        valid_release_year_files = []
        valid_tags_files = []

        for index in range(len(sys_arguments) - 2):
            if sys_arguments[index + 2].startswith("title="):  # The user has specified a custom criterion for the title
                cursor.execute("SELECT full_path FROM media WHERE INSTR(title, " + "\"" + sys_arguments[index + 2][6:]
                               + "\"" + ") > 0")

                for i in cursor.fetchall():  # Updating the corresponding list using the cursor result
                    if os.path.dirname(i[0]) == media_folder:
                        valid_title_files.append(i[0])

            # The user has specified a custom criterion for the artist
            if sys_arguments[index + 2].startswith("artist="):
                cursor.execute(
                    "SELECT full_path FROM media WHERE INSTR(artist, " + "\"" + sys_arguments[index + 2][7:] +
                    "\") > 0")

                for i in cursor.fetchall():  # Updating the corresponding list using the cursor result
                    if os.path.dirname(i[0]) == media_folder:
                        valid_artist_files.append(i[0])

            if sys_arguments[index + 2].startswith("album="):  # The user has specified a custom criterion for the album
                cursor.execute(
                    "SELECT full_path FROM media WHERE album = " + "\"" + sys_arguments[index + 2][6:] + "\"")

                for i in cursor.fetchall():  # Updating the corresponding list using the cursor result
                    if os.path.dirname(i[0]) == media_folder:
                        valid_album_files.append(i[0])

            # The user has specified a custom criterion for the release year
            if sys_arguments[index + 2].startswith("release_year="):
                cursor.execute(
                    "SELECT full_path FROM media WHERE release_date = " + "\"" + sys_arguments[index + 2][13:]
                    + "\"")

                for i in cursor.fetchall():  # Updating the corresponding list using the cursor result
                    if os.path.dirname(i[0]) == media_folder:
                        valid_release_year_files.append(i[0])

            if sys_arguments[index + 2].startswith("tags="):  # The user has specified a custom criterion for the tags
                tags_list = sys_arguments[index + 2][5:].replace('\"', '').replace(' ', '').split(",")

                for tag in tags_list:
                    cursor.execute("SELECT full_path FROM media WHERE INSTR(tags, \"" + tag + "\") > 0")

                    for i in cursor.fetchall():  # Updating the corresponding list using the cursor result
                        if os.path.dirname(i[0]) == media_folder:
                            valid_tags_files.append(i[0])

        # We are now performing intersection operation for each of the lists in order display only the files that match
        # every criterion passed by the user
        files = intersection(intersection(intersection(intersection(valid_title_files, valid_artist_files),
                                                       valid_album_files), valid_release_year_files), valid_tags_files)

        if not files:
            print("\nNo results.")
        else:
            for i in files:
                print("\n" + i)


if __name__ == "__main__":

    connection = connect_to_database()

    if connection:  # Only continue with app execution if database connection was successful

        # The value that stores the path of the media folder
        media_folder = config_var['MEDIA FOLDER']['folder']

        # The value that stores the run mode of the application
        menu_var = config_var['RUN-MODE']['run_mode']

        if len(sys.argv) == 1:  # If no arguments or options are passed, the application will run in loop mode
            if menu_var == "0" or menu_var == "2":  # In these run modes, the GUI needs to be loaded
                SongStorageGUI().mainloop()

            elif menu_var == "1":  # The application will run in command-line interface
                SongStorageCLI(1)

            else:  # An error in the configuration file has set "run_mode" to an invalid value. Resetting it to 0
                config_var.set("RUN-MODE", "run_mode", "0")

                with open('config.ini', 'w') as configfile:
                    config_var.write(configfile)  # Writing the changes to the configuration file
                    configfile.close()

                SongStorageGUI().mainloop()

        else:  # The application will run in CLI-mode, one single iteration
            SongStorageCLI(0)
