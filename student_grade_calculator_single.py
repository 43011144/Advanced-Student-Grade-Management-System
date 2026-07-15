import csv
import os
import sys
import threading
import unittest
import io

import tkinter as tk
from tkinter import ttk, messagebox


"""Question Number 1 - Data Module"""

# ====================== CSV FILE SETUP ======================

# Path to the CSV file used for persistent student data storage
CSV_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "students.csv")

# Column headers for the CSV file
FIELDNAMES = [
    "student_no",
    "name",
    "surname",
    "module",
    "quiz",
    "project",
    "final_exam",
    "practical",
    "overall_grade",
]

# Modules available for selection in the application
AVAILABLE_MODULES = [
    "C++ Programming",
    "Database Systems",
    "Python Programming",
    "Data Structures",
    "Operating Systems",
]

# Valid mark range boundaries
MARK_MIN = 0
MARK_MAX = 100


# ====================== CSV FUNCTIONS ======================

def ensure_csv_exists():
    """Create the CSV file with headers if it does not already exist."""
    if not os.path.exists(CSV_FILE):
        with open(CSV_FILE, mode="w", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=FIELDNAMES)
            writer.writeheader()


def load_all_students():
    """
    Read all student records from the CSV file.
    Returns a list of dictionaries, one per student.
    Raises FileNotFoundError if the file is missing.
    Raises ValueError if any row contains corrupt or incomplete data.
    """
    ensure_csv_exists()
    students = []
    with open(CSV_FILE, mode="r", newline="") as f:
        reader = csv.DictReader(f)
        for row_number, row in enumerate(reader, start=2):
            validated = _validate_row(row, row_number)
            students.append(validated)
    return students


def save_student(student_dict):
    """
    Append a single validated student record to the CSV file.
    Raises ValueError if validation fails.
    """
    ensure_csv_exists()
    _validate_row(student_dict)
    with open(CSV_FILE, mode="a", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=FIELDNAMES)
        writer.writerow(student_dict)


def delete_student(student_no):
    """
    Remove the record matching student_no from the CSV file.
    Raises ValueError if the student number is not found.
    """
    ensure_csv_exists()
    students = load_all_students()
    original_count = len(students)
    # Filter out the student with the matching student number
    students = [
        s for s in students
        if s["student_no"].strip().lower() != student_no.strip().lower()
    ]
    if len(students) == original_count:
        raise ValueError(f"Student number '{student_no}' was not found.")
    _rewrite_csv(students)


def search_student(student_no):
    """
    Return the first student record matching student_no, or None if not found.
    """
    students = load_all_students()
    for student in students:
        if student["student_no"].strip().lower() == student_no.strip().lower():
            return student
    return None


def update_student_mark(student_no, assessment, new_mark):
    """
    Update a single assessment mark for the given student and
    recalculate the overall grade automatically.
    assessment must be one of: 'quiz', 'project', 'final_exam', 'practical'.
    Raises ValueError for invalid inputs or a missing student.
    """
    valid_assessments = ["quiz", "project", "final_exam", "practical"]
    if assessment not in valid_assessments:
        raise ValueError(f"Assessment must be one of: {valid_assessments}")

    # Validate the new mark before applying it
    new_mark = _parse_mark(new_mark, assessment)

    students = load_all_students()
    found = False
    for student in students:
        if student["student_no"].strip().lower() == student_no.strip().lower():
            student[assessment] = new_mark
            # Recalculate overall grade after the mark update
            student["overall_grade"] = calculate_overall_grade(
                student["quiz"],
                student["project"],
                student["final_exam"],
                student["practical"],
            )
            found = True
            break

    if not found:
        raise ValueError(f"Student number '{student_no}' was not found.")

    _rewrite_csv(students)


def student_no_exists(student_no):
    """Return True if a student with the given number already exists in the CSV."""
    return search_student(student_no) is not None


def _rewrite_csv(students):
    """Overwrite the entire CSV file with the supplied list of student dicts."""
    with open(CSV_FILE, mode="w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=FIELDNAMES)
        writer.writeheader()
        writer.writerows(students)


def _validate_row(row, row_number=None):
    """
    Validate a student record dictionary.
    Converts all numeric fields from string to float.
    Returns the validated dictionary or raises ValueError on any problem.
    """
    location = f" (row {row_number})" if row_number else ""

    # Check all required fields are present and not empty
    for field in FIELDNAMES:
        if field not in row or row[field] is None or str(row[field]).strip() == "":
            raise ValueError(f"Missing value for '{field}'{location}.")

    # Validate text fields
    if not str(row["student_no"]).strip():
        raise ValueError(f"Student number cannot be empty{location}.")
    if not str(row["name"]).strip():
        raise ValueError(f"Name cannot be empty{location}.")
    if not str(row["surname"]).strip():
        raise ValueError(f"Surname cannot be empty{location}.")
    if str(row["module"]).strip() not in AVAILABLE_MODULES:
        raise ValueError(
            f"Module '{row['module']}' is not valid{location}. "
            f"Choose from: {AVAILABLE_MODULES}"
        )

    # Validate and convert all numeric mark fields
    numeric_fields = ["quiz", "project", "final_exam", "practical", "overall_grade"]
    for field in numeric_fields:
        row[field] = _parse_mark(row[field], field, location)

    return row


def _parse_mark(value, field_name, location=""):
    """
    Parse and validate a single mark value.
    Returns the mark as a float.
    Raises ValueError if the value is not numeric or outside 0-100.
    """
    try:
        mark = float(value)
    except (ValueError, TypeError):
        raise ValueError(
            f"Mark for '{field_name}' must be a number{location}. Got: '{value}'"
        )
    if not (MARK_MIN <= mark <= MARK_MAX):
        raise ValueError(
            f"Mark for '{field_name}' must be between {MARK_MIN} and "
            f"{MARK_MAX}{location}. Got: {mark}"
        )
    return mark


"""Question Number 2 - Grade Calculations"""

# ====================== ASSESSMENT WEIGHTINGS ======================

# Weightings must always sum to 1.0 (100%)
WEIGHTS = {
    "quiz":       0.10,   # Quiz contributes 10%
    "project":    0.20,   # Project contributes 20%
    "final_exam": 0.50,   # Final Exam contributes 50%
    "practical":  0.20,   # Practical contributes 20%
}


# ====================== CALCULATION FUNCTIONS ======================

def calculate_overall_grade(quiz, project, final_exam, practical):
    """
    Calculate the weighted overall grade for a single student.
    Each mark is multiplied by its weighting then summed.
    Returns the result rounded to one decimal place.
    Raises ValueError if any mark is missing or outside 0-100.
    """
    marks = {
        "quiz":       quiz,
        "project":    project,
        "final_exam": final_exam,
        "practical":  practical,
    }

    # Validate every mark before computing the weighted sum
    for field, value in marks.items():
        if value is None or str(value).strip() == "":
            raise ValueError(f"Mark for '{field}' is missing.")
        marks[field] = _parse_mark(value, field)

    overall = sum(marks[field] * WEIGHTS[field] for field in WEIGHTS)
    return round(overall, 1)


def get_grade_symbol(overall_grade):
    """
    Return the performance category for a given overall percentage.
    Grading scale:
        75 - 100  ->  Distinction
        65 - 74   ->  Merit
        50 - 64   ->  Pass
        0  - 49   ->  Fail
    """
    if overall_grade >= 75:
        return "Distinction"
    elif overall_grade >= 65:
        return "Merit"
    elif overall_grade >= 50:
        return "Pass"
    else:
        return "Fail"


def calculate_grades_batch(students, callback=None):
    """
    Calculate overall grades for a list of student dictionaries using
    multi-threading so each student is processed in its own thread.
    students : list of dicts containing quiz, project, final_exam, practical.
    callback : optional function called with the completed results list.
    Returns the updated list with overall_grade populated for each student.
    """
    results = [None] * len(students)
    threads = []

    def _process(index, student):
        """Worker function executed in a separate thread for each student."""
        try:
            grade = calculate_overall_grade(
                student["quiz"],
                student["project"],
                student["final_exam"],
                student["practical"],
            )
            updated = dict(student)
            updated["overall_grade"] = grade
            results[index] = updated
        except ValueError:
            # Keep the original record if the grade cannot be calculated
            results[index] = student

    # Create and start one thread per student
    for i, student in enumerate(students):
        t = threading.Thread(target=_process, args=(i, student))
        threads.append(t)
        t.start()

    # Wait for all threads to finish before returning
    for t in threads:
        t.join()

    if callback:
        callback(results)

    return results


def get_assessment_breakdown(student):
    """
    Return a formatted string showing each assessment's weighted contribution
    alongside the final overall grade and performance symbol.
    """
    lines = [
        f"  Quiz        (10%):  {student['quiz']}  ->  weighted {round(student['quiz'] * WEIGHTS['quiz'], 2)}",
        f"  Project     (20%):  {student['project']}  ->  weighted {round(student['project'] * WEIGHTS['project'], 2)}",
        f"  Final Exam  (50%):  {student['final_exam']}  ->  weighted {round(student['final_exam'] * WEIGHTS['final_exam'], 2)}",
        f"  Practical   (20%):  {student['practical']}  ->  weighted {round(student['practical'] * WEIGHTS['practical'], 2)}",
        f"  Overall Grade:      {student['overall_grade']}  ({get_grade_symbol(student['overall_grade'])})",
    ]
    return "\n".join(lines)


"""Question Number 3 - User Interface"""

# ====================== GUI STYLE CONSTANTS ======================

# Background colours
BG_MAIN         = "#F0F4F8"   # Main window background
BG_HEADER       = "#1A2B4A"   # Dark header banner
BG_FORM         = "#FFFFFF"   # Form / input area background
BG_TABLE        = "#FFFFFF"   # Table row colour (even)
BG_ROW_ALT      = "#EAF1F8"   # Table row colour (odd)
BG_ROW_SELECTED = "#C8DCF0"   # Highlighted / selected row

# Button colour definitions (background, foreground, active background)
BTN_CAPTURE = {"bg": "#2E7D32", "fg": "#FFFFFF", "activebackground": "#1B5E20"}
BTN_VIEW    = {"bg": "#1565C0", "fg": "#FFFFFF", "activebackground": "#0D47A1"}
BTN_SEARCH  = {"bg": "#E65100", "fg": "#FFFFFF", "activebackground": "#BF360C"}
BTN_CLOSE   = {"bg": "#B71C1C", "fg": "#FFFFFF", "activebackground": "#7F0000"}
BTN_SAVE    = {"bg": "#2E7D32", "fg": "#FFFFFF", "activebackground": "#1B5E20"}
BTN_UPDATE  = {"bg": "#E65100", "fg": "#FFFFFF", "activebackground": "#BF360C"}
BTN_DELETE  = {"bg": "#B71C1C", "fg": "#FFFFFF", "activebackground": "#7F0000"}
BTN_TESTS   = {"bg": "#6A1B9A", "fg": "#FFFFFF", "activebackground": "#4A148C"}

# Text colours
FG_LABEL    = "#1A2B4A"   # Standard label text
FG_TITLE    = "#FFFFFF"   # Header title text
FG_SUCCESS  = "#2E7D32"   # Success / saved message
FG_ERROR    = "#B71C1C"   # Error / validation message

# Font definitions
FONT_TITLE  = ("Segoe UI", 16, "bold")
FONT_SUB    = ("Segoe UI", 10)
FONT_HEAD   = ("Segoe UI", 11, "bold")
FONT_LABEL  = ("Segoe UI", 10)
FONT_INPUT  = ("Segoe UI", 10)
FONT_BTN    = ("Segoe UI", 10, "bold")
FONT_TABLE  = ("Segoe UI", 9)
FONT_OK     = ("Segoe UI", 10, "bold")
FONT_SMALL  = ("Segoe UI", 9)

# Layout spacing
PAD    = 16   # Outer padding for form frames
ENTRY_W = 28  # Character width for entry fields
BTN_W   = 22  # Character width for main menu buttons


# ====================== SHARED GUI HELPER FUNCTIONS ======================

def _center(window, width, height, parent=None):
    """Centre a window on screen or over a parent window."""
    window.update_idletasks()
    if parent:
        x = parent.winfo_rootx() + (parent.winfo_width()  - width)  // 2
        y = parent.winfo_rooty() + (parent.winfo_height() - height) // 2
    else:
        x = (window.winfo_screenwidth()  - width)  // 2
        y = (window.winfo_screenheight() - height) // 2
    window.geometry(f"{width}x{height}+{x}+{y}")


def _header(parent, text):
    """Build the dark header banner used at the top of every window."""
    frm = tk.Frame(parent, bg=BG_HEADER)
    frm.pack(fill="x")
    tk.Label(frm, text=text, font=FONT_HEAD, bg=BG_HEADER,
             fg=FG_TITLE, pady=12).pack()
    return frm


def _btn(parent, text, style, command, width=None, padx=14, pady=6):
    """Create and return a consistently styled flat button."""
    kw = dict(
        text=text, font=FONT_BTN,
        bg=style["bg"], fg=style["fg"],
        activebackground=style["activebackground"],
        activeforeground="#FFFFFF",
        relief="flat", cursor="hand2",
        command=command, padx=padx, pady=pady,
    )
    if width:
        kw["width"] = width
    return tk.Button(parent, **kw)


# ====================== TABLE COLUMN SPECIFICATION ======================

# Shared column config used by both the View/Delete and Search/Update windows
# Format: (header label, data key, column width in pixels)
TABLE_COLS = [
    ("Student No",       "student_no",    110),
    ("Name",             "name",           80),
    ("Surname",          "surname",        90),
    ("Module",           "module",        145),
    ("Quiz(10%)",        "quiz",           70),
    ("Project(20%)",     "project",        80),
    ("Final Exam(50%)",  "final_exam",     95),
    ("Practical(20%)",   "practical",      85),
    ("Overall Grade",    "overall_grade",  90),
]


def _build_treeview(parent, height=8):
    """
    Create a Treeview table with vertical and horizontal scrollbars.
    Applies alternating row colours for readability.
    Returns the Treeview widget.
    """
    col_ids = [c[1] for c in TABLE_COLS]

    frm = tk.Frame(parent, bg=BG_MAIN)
    frm.pack(fill="both", expand=True, padx=12)

    scroll_y = ttk.Scrollbar(frm, orient="vertical")
    scroll_x = ttk.Scrollbar(frm, orient="horizontal")

    tree = ttk.Treeview(
        frm, columns=col_ids, show="headings",
        height=height,
        yscrollcommand=scroll_y.set,
        xscrollcommand=scroll_x.set,
        selectmode="browse",
    )
    scroll_y.config(command=tree.yview)
    scroll_x.config(command=tree.xview)

    # Set heading labels and column widths
    for heading, col_id, width in TABLE_COLS:
        tree.heading(col_id, text=heading, anchor="center")
        tree.column(col_id, width=width, anchor="center", minwidth=50)

    # Configure alternating row background colours
    tree.tag_configure("even",  background=BG_TABLE)
    tree.tag_configure("odd",   background=BG_ROW_ALT)
    tree.tag_configure("found", background=BG_ROW_SELECTED)

    tree.pack(side="left", fill="both", expand=True)
    scroll_y.pack(side="right", fill="y")

    # Horizontal scrollbar sits below the table
    scroll_x_frm = tk.Frame(parent, bg=BG_MAIN)
    scroll_x_frm.pack(fill="x", padx=12)

    return tree


# ====================== MAIN MENU ======================

class MainMenuWindow(tk.Tk):
    """
    Root application window.
    Displays the main navigation menu with buttons for each feature.
    """

    def __init__(self):
        super().__init__()
        self.title("Eduvos Student Grade Calculator")
        self.resizable(False, False)
        self.configure(bg=BG_MAIN)
        _center(self, 420, 460)
        self._build_ui()

    def _build_ui(self):
        """Build the header banner and navigation buttons."""
        # Header section
        hdr = tk.Frame(self, bg=BG_HEADER)
        hdr.pack(fill="x")
        tk.Label(hdr, text="Eduvos Student Grade Calculator",
                 font=FONT_TITLE, bg=BG_HEADER, fg=FG_TITLE, pady=16).pack()
        tk.Label(hdr, text="2026 Final Project 2",
                 font=FONT_SUB, bg=BG_HEADER, fg="#A0B4CC", pady=0).pack()
        tk.Label(hdr, text="Manage Student Marks Easily",
                 font=FONT_SUB, bg=BG_HEADER, fg="#A0B4CC", pady=6).pack()

        # Navigation buttons
        frm = tk.Frame(self, bg=BG_MAIN, pady=28)
        frm.pack(fill="both", expand=True)

        buttons = [
            ("Capture Student Marks",   BTN_CAPTURE, self._open_capture),
            ("View / Delete Records",   BTN_VIEW,    self._open_view_delete),
            ("Search / Update Records", BTN_SEARCH,  self._open_search_update),
            ("Run Tests",               BTN_TESTS,   self._open_tests),
            ("Close Application",       BTN_CLOSE,   self.destroy),
        ]
        for text, style, cmd in buttons:
            _btn(frm, text, style, cmd, width=BTN_W, pady=10).pack(pady=7)

    def _open_capture(self):
        """Open the Capture Student Marks window."""
        CaptureWindow(self)

    def _open_view_delete(self):
        """Open the View / Delete Records window."""
        ViewDeleteWindow(self)

    def _open_search_update(self):
        """Open the Search / Update Records window."""
        SearchUpdateWindow(self)

    def _open_tests(self):
        """Open the Unit Test Results window."""
        TestResultWindow(self)


# ====================== CAPTURE WINDOW ======================

class CaptureWindow(tk.Toplevel):
    """
    Form window for entering and saving a new student record.
    Calculates and displays the overall grade after a successful save.
    """

    def __init__(self, parent):
        super().__init__(parent)
        self.title("Capture Student Marks")
        self.resizable(False, False)
        self.configure(bg=BG_MAIN)
        self.grab_set()  # Make this window modal
        _center(self, 430, 520, parent)
        self._build_ui()

    def _build_ui(self):
        """Build the input form with all student fields and the Save button."""
        _header(self, "Capture Student Marks")

        form = tk.Frame(self, bg=BG_FORM, padx=PAD, pady=PAD)
        form.pack(fill="both", expand=True, padx=12, pady=12)

        # Field definitions: (label text, data key, widget type)
        fields = [
            ("Student No:",        "student_no", "entry"),
            ("Name:",              "name",       "entry"),
            ("Surname:",           "surname",    "entry"),
            ("Module:",            "module",     "combo"),
            ("Quiz (10%):",        "quiz",       "entry"),
            ("Project (20%):",     "project",    "entry"),
            ("Final Exam (50%):",  "final_exam", "entry"),
            ("Practical (20%):",   "practical",  "entry"),
        ]

        self._vars = {}
        for i, (label, attr, kind) in enumerate(fields):
            tk.Label(form, text=label, font=FONT_LABEL, bg=BG_FORM,
                     fg=FG_LABEL, anchor="w", width=18).grid(
                row=i, column=0, sticky="w", pady=5)

            var = tk.StringVar()
            if kind == "combo":
                # Module field uses a dropdown restricted to valid options
                w = ttk.Combobox(form, textvariable=var,
                                 values=AVAILABLE_MODULES,
                                 state="readonly", width=ENTRY_W - 2,
                                 font=FONT_INPUT)
                w.current(0)
            else:
                w = tk.Entry(form, textvariable=var, font=FONT_INPUT,
                             width=ENTRY_W, relief="solid", bd=1)
            w.grid(row=i, column=1, sticky="w", pady=5)
            self._vars[attr] = var

        # Status label displays success or error after save attempt
        self._status_var = tk.StringVar()
        self._status_lbl = tk.Label(form, textvariable=self._status_var,
                                    font=FONT_OK, bg=BG_FORM)
        self._status_lbl.grid(row=len(fields), column=0, columnspan=2, pady=(10, 0))

        _btn(form, "Save", BTN_SAVE, self._save, width=16, pady=8).grid(
            row=len(fields) + 1, column=0, columnspan=2, pady=(10, 0))

    def _save(self):
        """
        Validate all fields, calculate the overall grade, and save the record.
        Shows the overall grade on success or an error message on failure.
        """
        raw = {attr: var.get().strip() for attr, var in self._vars.items()}

        # Check no field has been left empty
        for field, value in raw.items():
            if not value:
                self._status(f"Please fill in: {field.replace('_', ' ').title()}", True)
                return

        # Prevent duplicate student numbers
        if student_no_exists(raw["student_no"]):
            self._status(f"Student No '{raw['student_no']}' already exists.", True)
            return

        # Calculate overall grade (also validates mark ranges)
        try:
            overall = calculate_overall_grade(
                raw["quiz"], raw["project"], raw["final_exam"], raw["practical"])
        except ValueError as e:
            self._status(str(e), True)
            return

        # Build the complete student record dictionary
        record = {
            "student_no":    raw["student_no"],
            "name":          raw["name"],
            "surname":       raw["surname"],
            "module":        raw["module"],
            "quiz":          float(raw["quiz"]),
            "project":       float(raw["project"]),
            "final_exam":    float(raw["final_exam"]),
            "practical":     float(raw["practical"]),
            "overall_grade": overall,
        }

        try:
            save_student(record)
        except (ValueError, IOError) as e:
            self._status(str(e), True)
            return

        # Show the saved overall grade and clear the form for the next entry
        self._status(f"Saved. Overall Grade : {overall}", False)
        for attr, var in self._vars.items():
            if attr != "module":
                var.set("")

    def _status(self, msg, error):
        """Update the status label with a success (green) or error (red) message."""
        self._status_var.set(msg)
        self._status_lbl.configure(fg=FG_ERROR if error else FG_SUCCESS)


# ====================== VIEW / DELETE WINDOW ======================

class ViewDeleteWindow(tk.Toplevel):
    """
    Window that loads all student records into a table.
    Allows the user to select a row and delete that student record.
    """

    def __init__(self, parent):
        super().__init__(parent)
        self.title("View / Delete Students")
        self.resizable(True, True)
        self.configure(bg=BG_MAIN)
        self.grab_set()
        _center(self, 900, 420, parent)
        self._build_ui()
        self._load()  # Populate the table on open

    def _build_ui(self):
        """Build the table and Delete button."""
        _header(self, "View / Delete Student Records")
        self._tree = _build_treeview(self, height=10)

        bar = tk.Frame(self, bg=BG_MAIN, padx=12, pady=8)
        bar.pack(fill="x")

        # Record count label shown on the left
        self._status_var = tk.StringVar()
        tk.Label(bar, textvariable=self._status_var, font=FONT_SMALL,
                 bg=BG_MAIN, fg=FG_LABEL).pack(side="left")

        # Delete button sits on the right of the status bar
        _btn(bar, "Delete Selected", BTN_DELETE, self._delete).pack(side="right")

    def _load(self):
        """Clear the table and reload all records from the CSV file."""
        for item in self._tree.get_children():
            self._tree.delete(item)
        try:
            students = load_all_students()
        except (FileNotFoundError, ValueError) as e:
            self._status_var.set(f"Error: {e}")
            return
        if not students:
            self._status_var.set("No student records found.")
            return
        for i, s in enumerate(students):
            tag = "even" if i % 2 == 0 else "odd"
            self._tree.insert("", "end",
                              values=tuple(s[c[1]] for c in TABLE_COLS),
                              tags=(tag,))
        self._status_var.set(f"{len(students)} record(s) loaded.")

    def _delete(self):
        """Delete the selected student record after confirmation."""
        sel = self._tree.selection()
        if not sel:
            messagebox.showwarning("No Selection",
                                   "Please select a student record to delete.",
                                   parent=self)
            return

        vals = self._tree.item(sel[0], "values")
        student_no = vals[0]
        name = f"{vals[1]} {vals[2]}"

        # Ask for confirmation before deleting
        if not messagebox.askyesno("Confirm Delete",
                                   f"Delete record for {name} ({student_no})?\n"
                                   "This action cannot be undone.", parent=self):
            return

        try:
            delete_student(student_no)
        except ValueError as e:
            messagebox.showerror("Delete Failed", str(e), parent=self)
            return

        # Refresh the table to reflect the deletion
        self._load()
        messagebox.showinfo("Deleted", f"Record for {name} has been deleted.",
                            parent=self)


# ====================== SEARCH / UPDATE WINDOW ======================

# Maps the dropdown display label to the CSV data key
ASSESSMENT_OPTIONS = {
    "Quiz(10%)":        "quiz",
    "Project(20%)":     "project",
    "Final Exam(50%)":  "final_exam",
    "Practical(20%)":   "practical",
}


class SearchUpdateWindow(tk.Toplevel):
    """
    Window for searching a student by their student number and
    updating any single assessment mark for that student.
    The overall grade is recalculated automatically after an update.
    """

    def __init__(self, parent):
        super().__init__(parent)
        self.title("Search & Update Marks")
        self.resizable(False, False)
        self.configure(bg=BG_MAIN)
        self.grab_set()
        _center(self, 900, 500, parent)
        self._current = None  # Holds the currently found student record
        self._build_ui()

    def _build_ui(self):
        """Build the search bar, results table, and update controls."""
        _header(self, "Search & Update Student Marks")

        # Search bar row
        sr = tk.Frame(self, bg=BG_MAIN, padx=14, pady=10)
        sr.pack(fill="x")
        tk.Label(sr, text="Search by Student No:", font=FONT_LABEL,
                 bg=BG_MAIN, fg=FG_LABEL).pack(side="left")
        self._search_var = tk.StringVar()
        tk.Entry(sr, textvariable=self._search_var, font=FONT_INPUT,
                 width=20, relief="solid", bd=1).pack(side="left", padx=10)
        _btn(sr, "Search", BTN_SEARCH, self._search, padx=12, pady=4).pack(side="left")

        # Results table (shows one row for the found student)
        self._tree = _build_treeview(self, height=5)

        # Update controls section
        uf = tk.Frame(self, bg=BG_MAIN, padx=14, pady=10)
        uf.pack(fill="x")

        tk.Label(uf, text="Select Assessment:", font=FONT_LABEL,
                 bg=BG_MAIN, fg=FG_LABEL, width=18, anchor="w").grid(
            row=0, column=0, sticky="w", pady=5)
        self._assessment_var = tk.StringVar()
        combo = ttk.Combobox(uf, textvariable=self._assessment_var,
                             values=list(ASSESSMENT_OPTIONS.keys()),
                             state="readonly", width=22, font=FONT_INPUT)
        combo.current(0)
        combo.grid(row=0, column=1, sticky="w", pady=5)

        tk.Label(uf, text="New Mark:", font=FONT_LABEL,
                 bg=BG_MAIN, fg=FG_LABEL, width=18, anchor="w").grid(
            row=1, column=0, sticky="w", pady=5)
        self._mark_var = tk.StringVar()
        tk.Entry(uf, textvariable=self._mark_var, font=FONT_INPUT,
                 width=24, relief="solid", bd=1).grid(
            row=1, column=1, sticky="w", pady=5)

        _btn(uf, "Update Mark", BTN_UPDATE, self._update, padx=14, pady=6).grid(
            row=2, column=0, columnspan=2, sticky="w", pady=8)

        # Status label at the bottom of the window
        self._status_var = tk.StringVar()
        self._status_lbl = tk.Label(self, textvariable=self._status_var,
                                    font=FONT_OK, bg=BG_MAIN)
        self._status_lbl.pack(pady=4)

    def _search(self):
        """Search the CSV for the entered student number and display the result."""
        sno = self._search_var.get().strip()
        if not sno:
            self._status("Please enter a student number.", True)
            return

        # Clear any previous search result
        for item in self._tree.get_children():
            self._tree.delete(item)
        self._current = None
        self._mark_var.set("")

        try:
            student = search_student(sno)
        except (FileNotFoundError, ValueError) as e:
            self._status(str(e), True)
            return

        if student is None:
            messagebox.showinfo("Not Found", "Student not found.", parent=self)
            self._status("Student not found.", True)
            return

        # Display the found student in the table and highlight the row
        iid = self._tree.insert("", "end",
                                values=tuple(student[c[1]] for c in TABLE_COLS),
                                tags=("found",))
        self._tree.selection_set(iid)
        self._current = student

        self._status(
            f"Found: {student['name']} {student['surname']}  |  "
            f"Overall Grade: {student['overall_grade']}  "
            f"({get_grade_symbol(student['overall_grade'])})",
            False,
        )

    def _update(self):
        """Apply the new mark to the selected assessment and refresh the display."""
        if self._current is None:
            self._status("Search for a student first.", True)
            return

        new_mark = self._mark_var.get().strip()
        if not new_mark:
            self._status("Please enter a new mark.", True)
            return

        label = self._assessment_var.get()
        key   = ASSESSMENT_OPTIONS.get(label)

        try:
            update_student_mark(self._current["student_no"], key, new_mark)
        except ValueError as e:
            self._status(str(e), True)
            return

        messagebox.showinfo("Success", f"{label} updated successfully.", parent=self)

        # Re-run the search to refresh the table with the updated values
        self._search()

    def _status(self, msg, error):
        """Update the status label with a success (green) or error (red) message."""
        self._status_var.set(msg)
        self._status_lbl.configure(fg=FG_ERROR if error else FG_SUCCESS)


# ====================== TEST RESULT WINDOW ======================

class TestResultWindow(tk.Toplevel):
    """
    Window that runs the full unit test suite and displays the results
    in a scrollable terminal-style panel with colour-coded pass/fail output.
    """

    def __init__(self, parent):
        super().__init__(parent)
        self.title("Unit Test Results")
        self.resizable(True, True)
        self.configure(bg=BG_MAIN)
        self.grab_set()
        _center(self, 720, 540, parent)
        self._build_ui()
        self.after(100, self._run_tests)  # Run after the window finishes rendering

    def _build_ui(self):
        """Build the scrollable output area and Close button."""
        _header(self, "Unit Test Results - Deliverable 4")

        txt_frm = tk.Frame(self, bg=BG_MAIN, padx=12, pady=8)
        txt_frm.pack(fill="both", expand=True)

        scroll = ttk.Scrollbar(txt_frm)
        scroll.pack(side="right", fill="y")

        # Dark terminal-style text widget for test output
        self._text = tk.Text(
            txt_frm, font=("Courier New", 9), bg="#1E1E2E", fg="#CDD6F4",
            insertbackground="#CDD6F4", relief="flat",
            yscrollcommand=scroll.set, wrap="none",
        )
        self._text.pack(fill="both", expand=True)
        scroll.config(command=self._text.yview)

        # Colour tags for different output line types
        self._text.tag_configure("pass",    foreground="#A6E3A1")  # green for passed tests
        self._text.tag_configure("fail",    foreground="#F38BA8")  # red for failed tests
        self._text.tag_configure("error",   foreground="#FAB387")  # orange for errors
        self._text.tag_configure("summary", foreground="#89B4FA",  # blue for summary lines
                                 font=("Courier New", 9, "bold"))
        self._text.tag_configure("heading", foreground="#CBA6F7",  # purple for headings
                                 font=("Courier New", 9, "bold"))

        bar = tk.Frame(self, bg=BG_MAIN, pady=8)
        bar.pack()
        _btn(bar, "Close", BTN_CLOSE, self.destroy, padx=20, pady=6).pack()

    def _run_tests(self):
        """Execute all unit tests and display the output with colour coding."""
        self._text.configure(state="normal")
        self._text.delete("1.0", "end")
        self._append("Running all unit tests...\n\n", "heading")

        # Capture the test runner output into a string buffer
        stream = io.StringIO()
        loader = unittest.TestLoader()
        suite  = loader.loadTestsFromTestCase(TestGradeCalculator)
        runner = unittest.TextTestRunner(stream=stream, verbosity=2)
        result = runner.run(suite)

        output = stream.getvalue()

        # Apply colour tags based on the content of each output line
        for line in output.splitlines():
            if " ... ok" in line or line.endswith("ok"):
                self._append(line + "\n", "pass")
            elif "FAIL" in line or "ERROR" in line:
                self._append(line + "\n", "fail")
            elif line.startswith("---") or line.startswith("==="):
                self._append(line + "\n", "summary")
            elif "Ran" in line or "OK" in line or "FAILED" in line:
                self._append(line + "\n", "summary")
            else:
                self._append(line + "\n")

        # Show the final pass / fail count
        passed = result.testsRun - len(result.failures) - len(result.errors)
        total  = result.testsRun
        summary = f"\n  {passed} / {total} tests passed"
        tag = "pass" if result.wasSuccessful() else "fail"
        self._append(summary + "\n", tag)

        self._text.configure(state="disabled")

    def _append(self, text, tag=None):
        """Append a line of text to the output widget with an optional colour tag."""
        if tag:
            self._text.insert("end", text, tag)
        else:
            self._text.insert("end", text)
        self._text.see("end")


"""Question Number 4 - Testing and Documentation"""

# ====================== UNIT TESTS ======================

class TestGradeCalculator(unittest.TestCase):
    """
    Unit tests for all calculation and validation logic.
    Covers normal cases, boundary values, and invalid/missing input.
    Run by clicking Run Tests on the main menu, or directly in PyCharm.
    """

    # --- calculate_overall_grade ---

    def test_standard_calculation(self):
        """Known inputs produce the correct weighted result."""
        # 96*0.10 + 85*0.20 + 78*0.50 + 85*0.20 = 9.6 + 17 + 39 + 17 = 82.6
        self.assertAlmostEqual(calculate_overall_grade(96, 85, 78, 85), 82.6, places=1)

    def test_all_zeros_gives_zero(self):
        """All-zero marks must return 0.0."""
        self.assertEqual(calculate_overall_grade(0, 0, 0, 0), 0.0)

    def test_all_hundreds_gives_hundred(self):
        """All 100 marks must return 100.0."""
        self.assertEqual(calculate_overall_grade(100, 100, 100, 100), 100.0)

    def test_minimum_passing_boundary(self):
        """Result must be rounded to one decimal place."""
        self.assertEqual(calculate_overall_grade(50, 50, 50, 50), 50.0)

    def test_string_numeric_inputs_accepted(self):
        """String representations of numbers must be accepted."""
        self.assertAlmostEqual(calculate_overall_grade("96", "85", "78", "85"), 82.6, places=1)

    def test_weights_sum_to_one(self):
        """WEIGHTS dictionary must sum to exactly 1.0."""
        self.assertAlmostEqual(sum(WEIGHTS.values()), 1.0, places=10)

    def test_missing_quiz_raises(self):
        """An empty quiz mark must raise ValueError."""
        with self.assertRaises(ValueError):
            calculate_overall_grade("", 85, 78, 85)

    def test_none_mark_raises(self):
        """A None mark must raise ValueError."""
        with self.assertRaises(ValueError):
            calculate_overall_grade(None, 85, 78, 85)

    def test_mark_above_100_raises(self):
        """A mark above 100 must raise ValueError."""
        with self.assertRaises(ValueError):
            calculate_overall_grade(101, 85, 78, 85)

    def test_negative_mark_raises(self):
        """A negative mark must raise ValueError."""
        with self.assertRaises(ValueError):
            calculate_overall_grade(-1, 85, 78, 85)

    def test_non_numeric_raises(self):
        """A non-numeric string must raise ValueError."""
        with self.assertRaises(ValueError):
            calculate_overall_grade("abc", 85, 78, 85)

    def test_fractional_marks_handled(self):
        """Decimal mark inputs must be handled correctly."""
        expected = round(72.5*0.10 + 80.0*0.20 + 65.5*0.50 + 90.0*0.20, 1)
        self.assertAlmostEqual(
            calculate_overall_grade(72.5, 80.0, 65.5, 90.0), expected, places=1)

    def test_boundary_zero_is_valid(self):
        """0 is a valid mark and must not raise an error."""
        self.assertEqual(calculate_overall_grade(0, 0, 0, 0), 0.0)

    def test_boundary_100_is_valid(self):
        """100 is a valid mark and must not raise an error."""
        self.assertEqual(calculate_overall_grade(100, 100, 100, 100), 100.0)

    # --- get_grade_symbol ---

    def test_distinction_at_75(self):
        self.assertEqual(get_grade_symbol(75), "Distinction")

    def test_distinction_above_75(self):
        self.assertEqual(get_grade_symbol(90), "Distinction")

    def test_merit_at_65(self):
        self.assertEqual(get_grade_symbol(65), "Merit")

    def test_merit_at_74(self):
        self.assertEqual(get_grade_symbol(74), "Merit")

    def test_pass_at_50(self):
        self.assertEqual(get_grade_symbol(50), "Pass")

    def test_pass_at_64(self):
        self.assertEqual(get_grade_symbol(64), "Pass")

    def test_fail_at_49(self):
        self.assertEqual(get_grade_symbol(49), "Fail")

    def test_fail_at_zero(self):
        self.assertEqual(get_grade_symbol(0), "Fail")

    def test_perfect_score_is_distinction(self):
        self.assertEqual(get_grade_symbol(100), "Distinction")

    # --- calculate_grades_batch (multi-threading) ---

    def _student(self, no, q, pr, fe, pa):
        """Helper to create a minimal student dictionary for batch tests."""
        return {"student_no": no, "name": "T", "surname": "U",
                "module": "C++ Programming",
                "quiz": q, "project": pr, "final_exam": fe, "practical": pa,
                "overall_grade": 0}

    def test_batch_all_students_processed(self):
        """All students in a batch must have their overall_grade calculated."""
        students = [self._student("S1", 80, 70, 60, 90),
                    self._student("S2", 50, 60, 55, 40)]
        results = calculate_grades_batch(students)
        self.assertEqual(len(results), 2)
        for r in results:
            self.assertIsNotNone(r["overall_grade"])

    def test_batch_callback_invoked(self):
        """The optional callback must be called with the completed results."""
        called = []
        calculate_grades_batch([self._student("S1", 80, 70, 60, 90)],
                               callback=lambda r: called.extend(r))
        self.assertEqual(len(called), 1)

    def test_batch_empty_list(self):
        """An empty input list must return an empty result list."""
        self.assertEqual(calculate_grades_batch([]), [])

    def test_batch_correct_grade(self):
        """Batch must return the same grade as the single-student function."""
        results = calculate_grades_batch([self._student("S1", 96, 85, 78, 85)])
        self.assertAlmostEqual(results[0]["overall_grade"], 82.6, places=1)

    # --- _parse_mark ---

    def test_parse_valid_integer_string(self):
        """A valid integer string must be parsed to a float."""
        self.assertEqual(_parse_mark("75", "quiz"), 75.0)

    def test_parse_valid_float(self):
        """A valid float value must be returned unchanged."""
        self.assertEqual(_parse_mark(82.5, "project"), 82.5)

    def test_parse_invalid_string_raises(self):
        """A non-numeric string must raise ValueError."""
        with self.assertRaises(ValueError):
            _parse_mark("abc", "quiz")

    def test_parse_over_100_raises(self):
        """A mark over 100 must raise ValueError."""
        with self.assertRaises(ValueError):
            _parse_mark(105, "quiz")

    def test_parse_negative_raises(self):
        """A negative mark must raise ValueError."""
        with self.assertRaises(ValueError):
            _parse_mark(-5, "quiz")

    # --- _validate_row ---

    def test_validate_valid_row(self):
        """A complete, valid row must pass validation and convert marks to float."""
        row = {"student_no": "Eduv001", "name": "Ann", "surname": "Smith",
               "module": "C++ Programming",
               "quiz": "80", "project": "70", "final_exam": "65",
               "practical": "90", "overall_grade": "71.5"}
        validated = _validate_row(row)
        self.assertEqual(validated["quiz"], 80.0)

    def test_validate_missing_field_raises(self):
        """A row missing required fields must raise ValueError."""
        row = {"student_no": "Eduv002", "name": "Joe", "surname": "Soap",
               "module": "C++ Programming", "quiz": "70", "project": "80"}
        with self.assertRaises((ValueError, KeyError)):
            _validate_row(row)

    def test_validate_invalid_module_raises(self):
        """An unrecognised module name must raise ValueError."""
        row = {"student_no": "Eduv003", "name": "Jo", "surname": "Soap",
               "module": "Basket Weaving",
               "quiz": "70", "project": "80", "final_exam": "60",
               "practical": "75", "overall_grade": "68.0"}
        with self.assertRaises(ValueError):
            _validate_row(row)

    def test_validate_empty_student_no_raises(self):
        """An empty student number must raise ValueError."""
        row = {"student_no": "   ", "name": "Jo", "surname": "Soap",
               "module": "C++ Programming",
               "quiz": "70", "project": "80", "final_exam": "60",
               "practical": "75", "overall_grade": "68.0"}
        with self.assertRaises(ValueError):
            _validate_row(row)

    # --- get_assessment_breakdown ---

    def test_breakdown_contains_all_sections(self):
        """Breakdown string must include all four assessments and the overall grade."""
        s = {"student_no": "S1", "name": "A", "surname": "B",
             "module": "C++ Programming",
             "quiz": 80, "project": 70, "final_exam": 65,
             "practical": 90, "overall_grade": 71.5}
        breakdown = get_assessment_breakdown(s)
        for keyword in ("Quiz", "Project", "Final Exam", "Practical", "Overall Grade"):
            self.assertIn(keyword, breakdown)


# ====================== ENTRY POINT ======================

if __name__ == "__main__":
    if "--test" in sys.argv:
        # Run tests from the command line and print results to console
        suite  = unittest.TestLoader().loadTestsFromTestCase(TestGradeCalculator)
        runner = unittest.TextTestRunner(verbosity=2)
        result = runner.run(suite)
        sys.exit(0 if result.wasSuccessful() else 1)
    else:
        # Launch the GUI - this is what runs when you press Run in PyCharm
        app = MainMenuWindow()
        app.mainloop()
