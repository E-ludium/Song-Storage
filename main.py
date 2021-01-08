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

        # The button prompting the user to add media content to the media folder
        self.add_music_button = Button(self.path_frame_parent, text="Add Music...")
        self.header = Label(self.media_frame, text="Available media:")

        self.add_music_button.pack()

        self.process_widgets()

    # This method attempts a connection to the application's database, returning the connection is successful
    def connect_to_database(self):

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

    def process_widgets(self):  # Processes the widgets declared in the initialization method of the class
        self.init_frame.pack()

        self.folder_frame.pack()

        self.folder_locator.pack(side=LEFT)

        self.folder_button.pack(side=LEFT)

        self.media_folder_label.pack(side=LEFT)

        self.path_frame_parent.pack(side=LEFT)

        self.media_frame.pack(side=LEFT)

        self.header.pack()

    def folder_selector(self):  # Prompts the user to select the media folder
        folder = filedialog.askdirectory()  # We will use an OS-specific dialog box call to select the media folder
        
        self.config.set('MEDIA FOLDER', 'folder', folder)  # Updating the value inside the configuration file
        
        with open('config.ini', 'w') as configfile:   # Writing the changes to the configuration file
            self.config.write(configfile)

        self.display_media_folder()
        
    def display_media_folder(self):  # This method makes the media folder label display the correct folder

        # Updating the value of the variable storing the path to the media folder
        self.media_folder = self.config['MEDIA FOLDER']['folder']

        if self.media_folder != "":  # Checking if the user has previously selected a media folder
            self.folder_locator.pack_forget()
            self.folder_button.pack_forget()
            self.change_folder_button.pack(side=LEFT)

            # Updating the value of the variable that the media folder label will use
            self.var.set("Media folder: " + self.media_folder)


if __name__ == "__main__":
    SongStorage().mainloop()
