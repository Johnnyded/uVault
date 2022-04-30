"""
BeachHacks 2022
04/09/22

Alfredo Sequeida
Johnny Phamm
"""
from tkinter import *
from tkinter import filedialog
from tkinter import ttk
import os

from os import listdir
from os.path import isfile, join

# face api
import io
import uuid
from urllib.parse import urlparse

from PIL import Image, ImageTk
from azure.cognitiveservices.vision.face import FaceClient
from msrest.authentication import CognitiveServicesCredentials

# opecv
from cv2 import VideoCapture, imwrite, imencode, cvtColor, COLOR_BGR2RGB

import json


AUTH_USERS_DIR = "./auth_users"
AUTH = False
MAX_CHR_LIM = 8

top_win = None
msg_win = None
frm = None

root = Tk()
root.title("uVault")
root.geometry("400x300")
root.eval("tk::PlaceWindow . center")
img = PhotoImage(file="./icon_alt.png")
root.wm_iconphoto(True, img)

cam = VideoCapture(0)
var = IntVar()

context_selection = None


def get_from_config(get):
    """Get attribute from json config
    :param get the value to get from the config
    """
    with open("config.json") as config:
        config_file = json.load(config)
        return config_file.get(get)


KEY = get_from_config("key")
ENDPOINT = get_from_config("end_point")
print(KEY, ENDPOINT)
face_client = FaceClient(ENDPOINT, CognitiveServicesCredentials(KEY))


def save_photo():
    """
    save photo with a random uuid file name to use for face id verification
    """
    pop_up("Look at the camera and hold still")
    isExist = os.path.exists(AUTH_USERS_DIR)
    if not isExist:
        os.makedirs(AUTH_USERS_DIR)

    buffer = take_picture()
    with open(f"{AUTH_USERS_DIR}/{uuid.uuid4()}.jpg", "wb") as face:
        face.write(buffer.getbuffer())
    top_win.destroy()
    msg_win.destroy()


def set_to_config(k, v):
    """
    set attribute in json config
    :param k the key of the param
    :param v the value of the param
    """
    config_file = None

    with open("config.json") as config:
        config_file = json.load(config)
        config_file[k] = v

    with open("config.json", "w") as config:
        json.dump(config_file, config)


def pass_auth(pass_text):
    """
    authenticate password
    :param pass_text the plain text password to authenticate
    """
    global AUTH

    AUTH = get_from_config("password") == pass_text

    if not AUTH:
        pop_up("invalid password")
        var.set(0)
        AUTH = False
    else:
        global top_win
        top_win.destroy()
        top_win = Toplevel(root)
        ttk.Button(
            top_win,
            text="take picture",
            command=save_photo,
        ).grid(column=0, row=1)
        add_user()

        var.set(1)


def set_password(pass_text):
    set_to_config("password", pass_text)
    set_to_config("first_run", False)
    top_win.destroy()


def enter_password():
    global top_win
    top_win = Toplevel(root)
    # top_win.eval("tk::PlaceWindow . center")
    top_win.title("Enter Password")
    frm = ttk.Frame(top_win, padding=10)
    frm.grid()
    ttk.Label(frm, text="Enter password").grid(column=0, row=0)
    pass_var = StringVar()
    ttk.Entry(frm, textvariable=pass_var).grid(row=0, column=1)

    if get_from_config("first_run"):
        submit = ttk.Button(
            frm, text="set new password", command=lambda: set_password(pass_var.get())
        )
    else:
        submit = ttk.Button(
            frm, text="enter", command=lambda: pass_auth(pass_var.get())
        )

    submit.grid(column=2, row=0)

    submit.wait_variable(var)


def take_picture():
    result, image = cam.read()
    ret, buf = imencode(".jpg", image)
    return io.BytesIO(buf)


def create_new_user():
    global AUTH
    enter_password()


def add_user():
    """
    Adding a new user to the list of authenticated users
    """
    top = Label(top_win)

    top.grid(row=0, column=0)
    cv2image = cvtColor(cam.read()[1], COLOR_BGR2RGB)
    img = Image.fromarray(cv2image)
    imgtk = ImageTk.PhotoImage(image=img)
    top.imgtk = imgtk
    top.configure(image=imgtk)
    top.after(20, add_user)


def verify_face(image_to_verify):
    """
    Verify face w/ Microsoft's Azure facial recognition API
    :param image_to_verify the image source to verify
    """
    try:
        target_image_file_names = [
            f for f in listdir(AUTH_USERS_DIR) if isfile(join(AUTH_USERS_DIR, f))
        ]

        # The source photos contain this person
        source_image_file_name1 = image_to_verify

        detected_faces1 = face_client.face.detect_with_stream(
            source_image_file_name1, detection_model="detection_03"
        )

        # Add the returned face's face ID
        source_image1_id = detected_faces1[0].face_id
        print(
            "{} face(s) detected from image {}.".format(
                len(detected_faces1), source_image_file_name1
            )
        )

        # List for the target face IDs (uuids)
        detected_faces_ids = []
        # Detect faces from target image url list, returns a list[DetectedFaces]
        for image_file_name in target_image_file_names:
            with open(f"{AUTH_USERS_DIR}/{image_file_name}", "rb") as face:
                # We use detection model 3 to get better performance.
                detected_faces = face_client.face.detect_with_stream(
                    face, detection_model="detection_03"
                )
                # Add the returned face's face ID
                detected_faces_ids.append(detected_faces[0].face_id)
                print(
                    "{} face(s) detected from image {}.".format(
                        len(detected_faces), image_file_name
                    )
                )

        verify_result_same = face_client.face.verify_face_to_face(
            source_image1_id, detected_faces_ids[0]
        )
        verified = verify_result_same.is_identical

        if not verified:
            pop_up("Unauthorized User Detected")

        return verified

    except IndexError:
        pop_up("face not detected")


def pop_up(message):
    """Displays a pop-up window with text
    :param message the message to display as a pop up
    """
    global msg_win
    msg_win = Toplevel(root)
    # msg_win.eval("tk::PlaceWindow . center")
    errorFrm = ttk.Frame(msg_win, padding=10)
    errorFrm.grid()

    ttk.Label(errorFrm, text=message).grid(column=0, row=0)


def open_app(_path):
    """open a program/file if the face id passes the test
    :param _path the path of the application / file to open
    """
    pop_up("Look at the camera and hold still")
    msg_win.update()
    if verify_face(take_picture()):
        os.startfile(_path)


def add_program():
    """
    Add program/files to list of programs/files
    """
    global frm
    file_path = filedialog.askopenfilename()
    if file_path:
        name = file_path.split("/")[-1].replace(".exe", "")
        programs = get_from_config("programs")
        programs[name] = file_path
        set_to_config("programs", programs)
        frm.destroy()
        load_programs()


def remove_program():
    """
    Remove programs in list
    """
    print("removing", context_selection)
    programs = get_from_config("programs")
    del programs[context_selection]
    set_to_config("programs", programs)
    frm.destroy()
    load_programs()


def context_menu(event, program):
    """
    Handles and Displays Right Click Tear-Off for removing buttons
    :param event the event from the right click
    :program the program passed in from the right click
    """
    global context_selection
    context_selection = program
    try:
        m.tk_popup(event.x_root, event.y_root)
    finally:
        m.grab_release()


def load_programs():
    """
    load programs that have been added
    """
    global frm

    frm = ttk.Frame(root, padding=10)
    frm.grid()
    # Add User Button
    ttk.Button(
        frm,
        text="add user",
        command=create_new_user,
    ).grid(column=1, row=0)

    ttk.Button(
        frm,
        text="add program",
        command=add_program,
    ).grid(column=1, row=1)

    row = 2
    column = 1
    for program, _path in get_from_config("programs").items():
        name = program[0:MAX_CHR_LIM]

        if len(program) > MAX_CHR_LIM:
            name += "..."

        btn = ttk.Button(
            frm,
            text=name,
            command=lambda p=_path: open_app(p),
        )
        btn.grid(column=column, row=row)

        row += 1

        btn.bind(
            "<Button-3>", lambda event, program=program: context_menu(event, program)
        )

        if row >= 10:
            column += 1
            row = 2


if __name__ == "__main__":

    load_programs()

    if get_from_config("first_run"):
        enter_password()

    # right click event
    m = Menu(root, tearoff=0)
    m.add_command(label="Remove program", command=remove_program)

    root.mainloop()
