"""Project Name: SongStorage
   Project ID: 9
   Project Difficulty: A
   Propose: NIP
"""

from tkinter import *
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
        
        # Declaring the variables the GUI will use
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
        self.change_folder_button = Button(self.folder_frame, text="Change...", command=self.folder_selector)

        # The frame that will display all the media content available inside the media folder
        self.media_frame = Frame()

        self.path_frame_parent = Frame(self.media_frame, relief=GROOVE, width=500, height=100, bd=1)

        self.header = Label(self.media_frame, text="Available media:")

        # This label will display when the user attempts to add an already-existent media file
        self.already_exists = Label(self.folder_frame, text="")

        self.library_items = []  # The array storing info for every media file (name, buttons, metadata etc.)

        self.process_widgets()

        self.folder_scan()

    def connect_to_database(self):

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

        self.media_folder_label.pack(side=LEFT)

        self.path_frame_parent.pack(side=LEFT)

        self.media_frame.pack(side=LEFT)

        self.header.pack()

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
                sql_command = ''' INSERT INTO media(title, artist, album, release_date, full_path)
                                VALUES (?, ?, ?, ?, ?) '''

                values = (assumed_title, assumed_artist, '', '', full_path)

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
            Displays the entire list of media to the user.

            :return: None
        """

        # Parsing the entire database and displaying every record that matches the current media folder
        cursor = self.connection.cursor()
        cursor.execute("SELECT COUNT(*) FROM media")

        number_of_entries = cursor.fetchone()  # This variable will store the amount of records in the database

        self.path_frame_parent = Frame(self.media_frame, relief=GROOVE, width=500, height=100, bd=1)
        self.path_frame_parent.pack()

        # The canvas will store every item in the media list
        self.canvas = Canvas(self.path_frame_parent)
        path_frame_child = Frame(self.canvas)

        # Adding a scrollbar in case the media list height exceeds the window height
        scrollbar = Scrollbar(self.path_frame_parent, orient="vertical", command=self.canvas.yview)
        self.canvas.configure(yscrollcommand=scrollbar.set)

        scrollbar.pack(side=RIGHT, fill=Y)
        self.canvas.pack(side=LEFT)
        self.canvas.create_window((0, 0), window=path_frame_child, anchor='nw')
        path_frame_child.bind("<Configure>", self.scroll_function)

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
                self.library_items.append(Label(path_frame_child, textvariable=label_entry))
                self.library_items[-1].grid(row=index, column=1)

                # Adding the play button specific to the current media item
                self.library_items.append(Button(path_frame_child, text="Play"))
                self.library_items[-1].grid(row=index, column=2, padx=10, pady=5)

                # Adding the configuration button specific to the current media item
                self.library_items.append(Button(path_frame_child, text="Configure"))
                self.library_items[-1].grid(row=index, column=3, padx=10, pady=5)

        # The button that allows the user to add media files from other sources
        add_music_button = Button(path_frame_child, text="Add Music...", command=self.add_media_dialog)
        add_music_button.grid(row=index + 1, column=1)

        cursor.close()

    def scroll_function(self, event):

        """
            Dictates the behavior for the scrollbar.

            :return: None
        """

        self.canvas.configure(scrollregion=self.canvas.bbox("all"), width=400, height=200)

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


if __name__ == "__main__":
    SongStorage().mainloop()
