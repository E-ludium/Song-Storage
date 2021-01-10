"""Project Name: SongStorage
   Project ID: 9
   Project Difficulty: A
   Propose: NIP
"""

from tkinter import *
from tkinter import ttk
from tkinter import filedialog
import configparser
import sqlite3
from sqlite3 import Error
import os
import ntpath
import shutil


class SongStorage(Tk):  # The GUI class responsible for showing the interface to the user
    def __init__(self):
        super().__init__()
        self.title("Song Storage")
        
        """Declaring the variables needed for back-end"""
        # Variables tasked with processing the configuration file of the application
        self.config = configparser.ConfigParser()  # We will use a config file to store the path of the media folder
        self.config.read('config.ini')
        self.media_folder = self.config['MEDIA FOLDER']['folder']  # The value that stores the path of the media folder

        # Variable tasked with managing the database connected to the application
        self.connection = self.connect_to_database()
        
        """Declaring the variables the GUI will use"""
        self.init_frame = Frame()  # The main frame of the application
        self.folder_locator = Label(self.init_frame,
                                    text="Please choose the folder where you'd like to store your media: ")
        # This button will prompt the user to select a media folder
        self.folder_button = Button(self.init_frame, text="Browse...", command=self.folder_selector)
        
        self.folder_frame = Frame()  # The frame that will display the current media folder
        self.var = StringVar()  # The value that stores the current media folder's path as a string

        # The label that will display the current media folder
        self.media_folder_label = Label(self.folder_frame, textvariable=self.var)

        # The button that allows the user to change the currently selected media folder
        self.change_folder_button = ttk.Button(self.folder_frame, text="Change...", command=self.folder_selector)

        # The frame that will display all the media content available inside the media folder
        self.media_frame = Frame()
        self.canvas = Canvas()

        self.path_frame_parent = Frame(self.media_frame, relief=GROOVE, width=500, height=100, bd=1)

        self.header = Label(self.media_frame, text="Available media:")

        # This label will display when the user attempts to add an already-existent media file
        self.already_exists = Label(self.folder_frame, text="")

        # The button that allows the user to add media files from other sources
        self.add_music_button = ttk.Button(self.media_frame, text="Add Media...", command=self.add_media_dialog)

        # We are storing the length of the longest item in the media list in order to be able to modify the size of the
        # scrollable area (if necessary).
        self.longest_item_length = 0

        self.library_items = []  # The array storing info for every media file (name, buttons, metadata etc.)

        self.process_widgets()

        self.load_interface()

    @staticmethod
    def connect_to_database():

        """
            This method attempts a connection to the application's database, returning the connection if successful

            :return connection: Returns the variable pointing to the connection to the database.
        """

        # Attempting a connection to the database
        try:
            connection = sqlite3.connect('Resources/media.db')
        except Error as e:
            print(e)
            return

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
            cursor = connection.cursor()
            cursor.execute(create_table)
            connection.commit()
            cursor.close()
        except Error as e:
            print(e)

        # Returning the connection variable so that it can be used by other features of the application
        return connection

    def process_widgets(self):

        """
            Processes the widgets declared in the initialization method of the class.

            :return: None
        """

        self.init_frame.pack()

        self.folder_frame.pack()

        self.folder_locator.pack(side=LEFT)

        self.folder_button.pack(side=LEFT)

        self.media_folder_label.pack(side=LEFT, padx=10, pady=10)

        self.path_frame_parent.pack(side=LEFT)

        self.media_frame.pack(side=LEFT)

        self.header.pack(pady=10)

    def folder_scan(self):

        """
            Scans the currently selected media folder.
            For every media file it finds, it checks if the specified file is indexed to the database.
            If the file is not indexed (eg. it was manually placed by the user in the media folder), the program
            automatically adds it to the database and refreshes the list of available media.
        """

        cursor = self.connection.cursor()

        # Parsing the entire media folder and scanning each file
        for filename in os.listdir(self.media_folder):
            full_path = os.path.join(self.media_folder, filename).replace("\\", "/")

            # Checks if the file is indexed to the database
            cursor.execute("SELECT COUNT(1) FROM media WHERE full_path = \"" + full_path + "\"")
            result = int(str(cursor.fetchone())[1])

            if not result:  # If the file is not indexed, the program automatically adds it to the database
                self.add_media(full_path, 1)

        self.connection.commit()

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

        self.folder_scan()

        self.add_music_button.pack(pady=20)

    def add_media(self, file, mode):

        """
            Adds the file specified as parameter to the database.

            :param file: the file to be added to the database
            :param mode: the mode in which the algorithm runs.
                         '0' means the user is trying to copy a media file from another source folder.
                         '1' means the current file is already present in the media folder, but it's not indexed by the
                         database (this can happen if, for example, the user has manually placed a media file inside
                         the media folder).
        """

        if file.endswith('.mp3') or file.endswith('.wav'):  # Checking if the specified file is a valid media file
            assumed_title = ""  # This variable will store the title of the media
            assumed_artist = ""  # This variable will store the artist of the media

            if "-" in file:

                """ 
                    Usually, media files use a '-' character to split the title of the media and the artist.
                    This algorithm will attempt to automatically 'guess' the title and artist of the media if this
                    character is present.
                """

                if file.split("-")[0].endswith(" "):  # If there is a whitespace before the '-' character, we remove it
                    assumed_artist = ntpath.basename(file.split("-")[0][:-1])  # The auto-processed artist name
                else:
                    assumed_artist = ntpath.basename(file.split("-")[0])

                if file.split("-")[1].startswith(" "):  # If there is a whitespace after the '-' character, we remove it
                    assumed_title = file.split("-")[1][1:-4]  # The auto-processed media title
                else:
                    assumed_title = file.split("-")[1][:-4]

            if not mode:  # The user is attempting to add media files from another directory
                try:
                    shutil.copy2(file, self.media_folder)
                except Error as e:
                    print(e)

            # Updating the database
            cursor = self.connection.cursor()

            full_path = os.path.join(self.media_folder, os.path.basename(file)).replace("\\", "/")

            cursor.execute("SELECT COUNT(1) FROM media WHERE full_path = \"" + full_path + "\"")
            result = int(str(cursor.fetchone())[1])

            if not result:  # The selected file is not present in the database; the program will attempt to add it
                sql_command = ''' INSERT INTO media(title, artist, album, release_date, tags, full_path)
                                VALUES (?, ?, ?, ?, ?, ?) '''

                values = (assumed_title, assumed_artist, '', '', '', full_path)

                cursor.execute(sql_command, values)

                self.connection.commit()

            else:  # The selected file already exists in the database; letting the user know
                # Updating the label that alerts the user about the presence of the media file
                self.already_exists.text = "There is already a song with this name in the media folder!"
                self.update_idletasks()

            self.library_items = []
            self.path_frame_parent.destroy()
            self.display_media()

    def display_media(self):

        """
            The core of the program's GUI.
            Displays the entire list of media files to the user.

            :return: None
        """

        self.longest_item_length = 0

        # Parsing the entire database and displaying every record that matches the current media folder
        cursor = self.connection.cursor()
        cursor.execute("SELECT COUNT(*) FROM media")

        number_of_entries = cursor.fetchone()  # This variable will store the amount of records in the database

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

        index = 0  # Using an index to determine the correct row in which every media item needs to be placed

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
            if (os.path.dirname(entry_path[0])) == self.config['MEDIA FOLDER']['folder']:

                # Adding the media item title to the media list
                cursor.execute("SELECT mode FROM media WHERE id = " + str(i + 1))
                mode = cursor.fetchone()

                if int(mode[0]):  # Displaying the media label using its metadata
                    self.library_items.append(Label(path_frame_child, textvariable=display_entry))
                    self.library_items[-1].grid(row=index, column=1)

                    current_item_length = len(display_entry.get())
                    if current_item_length > self.longest_item_length:
                        self.longest_item_length = current_item_length

                else:  # Displaying the media label using its filename
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
                self.library_items.append(Button(path_frame_child, text="Play"))
                self.library_items[-1].grid(row=index, column=2, padx=10, pady=5)

                # Adding the info button specific to the current media item
                self.library_items.append(Button(path_frame_child, text="Info"))
                self.library_items[-1].grid(row=index, column=3, padx=10, pady=5)

                # Adding the configuration button specific to the current media item
                self.library_items.append(Button(path_frame_child, text="Configure",
                                                 command=lambda media_title=label_entry.get(), path=entry_path[0]:
                                                 self.configure_media(media_title, path)))
                self.library_items[-1].grid(row=index, column=4, padx=10, pady=5)

                # Adding the removal button specific to the current media item
                self.library_items.append(Button(path_frame_child, text="Remove",
                                                 command=lambda media_title=label_entry.get(), path=entry_path[0]:
                                                 self.remove_media(media_title, path)))
                self.library_items[-1].grid(row=index, column=5, padx=10, pady=5)

        # Updating the width of the scrollable area
        path_frame_child.bind("<Configure>", lambda event, x=self.longest_item_length: self.scroll_function(event, x))

        # Refreshing the add button
        self.add_music_button.destroy()
        self.add_music_button = ttk.Button(self.media_frame, text="Add Media...", command=self.add_media_dialog)
        self.add_music_button.pack(pady=20)

        cursor.close()

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

    def folder_selector(self):

        """
            Prompts the user to select the media folder.

            :return: None
        """

        folder = filedialog.askdirectory()  # We will use an OS-specific dialog box call to select the media folder
        
        self.config.set('MEDIA FOLDER', 'folder', folder)  # Updating the value inside the configuration file
        
        with open('config.ini', 'w') as configfile:   # Writing the changes to the configuration file
            self.config.write(configfile)

        self.display_media_folder()

        self.folder_scan()
        
    def display_media_folder(self):

        """
            This method makes the media folder label display the correct folder.

            :return: None
        """

        # Updating the value of the variable storing the path to the media folder
        self.media_folder = self.config['MEDIA FOLDER']['folder']

        if self.media_folder != "":  # Checking if the user has previously selected a media folder
            self.folder_locator.pack_forget()
            self.folder_button.pack_forget()
            self.change_folder_button.pack(side=LEFT)

            # Updating the value of the variable that the media folder label will use
            self.var.set("Media folder: " + self.media_folder)

    def configure_media(self, label_entry, path):

        """
            Opens a window that allows the user to modify song metadata (such as title, artist, release date etc.)
            It also allows the user to specify whether the media file should be displayed using the provided metadata
            or based on the name of the file.

            Note: By default, every record added to the database will have its mode set to '0' (meaning the application
            will display media based on its metadata).

            :param label_entry: Specifies the name of the media item (used for naming the newly created window).
            :param path: Specifies the path of the media file (used for identifying the correct entry in the database).
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
                                            value=0, command=lambda x=metadata_frame, y=filename_frame, z=path,
                                            window=config_window: self.display_metadata_widgets(x, y, z, window))
        mode2_radiobutton = ttk.Radiobutton(radiobutton_frame, text="Display media using filename", variable=var,
                                            value=1, command=lambda x=metadata_frame, y=filename_frame, z=path,
                                            window=config_window: self.display_filename_widgets(x, y, z, window))

        # Retrieving the current mode of the media file from the database
        cursor = self.connection.cursor()
        cursor.execute("SELECT mode FROM media WHERE full_path = " + "\"" + path + "\"")

        mode = cursor.fetchone()

        if int(mode[0]):  # The media file is displayed using its metadata
            var.set("1")
            self.display_filename_widgets(metadata_frame, filename_frame, path, config_window)
        else:  # The media file is displayed using its filename
            var.set("0")
            self.display_metadata_widgets(metadata_frame, filename_frame, path, config_window)

        mode1_radiobutton.pack(side=LEFT, padx=10, pady=10)
        mode2_radiobutton.pack(padx=10, pady=10)

        config_window.mainloop()

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
        cursor = self.connection.cursor()

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
        cursor = self.connection.cursor()

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
            :return: None
        """

        new_path = ""  # The variable storing the new path for the media file (if necessary)

        if run_mode:  # The algorithm will rename the file inside the media folder as specified by the user
            new_path = os.path.join(os.path.dirname(media_path), path_value.get())  # New filename
            os.rename(media_path, new_path)

        # We will use the "media_path" argument of the method to determine which database record needs to be updated
        cursor = self.connection.cursor()

        cursor.execute("UPDATE media SET title = " + "\"" + title_value.get() + "\"" + ", artist = " + "\"" +
                       artist_value.get() + "\"" + ", album = " + "\"" + album_value.get() + "\"" + ", release_date = "
                       + "\"" + release_date_value.get() + "\"" + ", tags = " + "\"" + tags_value.get() + "\"" +
                       ", mode = " + str(mode) + " WHERE full_path = " + "\"" + media_path + "\"")
        if run_mode:  # Updating the full path in the database as well
            cursor.execute("UPDATE media SET full_path = " + "\"" + new_path + "\"" + " WHERE full_path = " + "\"" +
                           media_path + "\"")

        self.connection.commit()
        cursor.close()

        window.destroy()  # Unloading the configuration window

        # Reloading the media list of the root window
        self.library_items = []
        self.path_frame_parent.destroy()
        self.display_media()

    def add_media_dialog(self):

        """
            Prompts the user to select a media file to be added to the media list.

            :return: None
        """

        # Resetting the alert label
        self.already_exists.text = ""
        self.update_idletasks()

        file = filedialog.askopenfilename()

        self.add_media(file, 0)  # Adding the selected media file to the list

        if file:  # Checking whether the user has aborted the operation
            # Getting the path of the file with respect to the current media folder (since the "file" variable points
            # to the location of the source file)
            full_path = os.path.join(self.media_folder, os.path.basename(file)).replace("\\", "/")

            # Whenever a media item is added, the user is automatically prompted to configure its metadata
            self.configure_media(os.path.basename(file), full_path)


if __name__ == "__main__":
    SongStorage().mainloop()
