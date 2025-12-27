# gui.py — KenKen Solver gui using CA and BT algorithms 
# ---------------------------------------------------------------------------

import threading
import tkinter as tk
from tkinter import ttk, messagebox, filedialog
from datetime import datetime

from utils import PUZZLES
from algorithm1 import cultural_algorithm
from algorithm2 import compute_animation_sequence

CELL_SIZE = 70
FONT_NUM = ("Arial", 24, "bold")
FONT_CAGE = ("Arial", 12)
BT_DELAY = 60  # BT animation speed in ms


class KenKenGUI:
    def __init__(self, root):
        self.root = root
        root.title("KenKen Solver — Final Enhanced Version")

        root.geometry("1450x900")
        root.minsize(900, 700)

        # canvases for CA (left) and BT (right)
        self.canvas_left = None
        self.canvas_right = None

        # text IDs for drawing numbers
        self.cell_text_left = []
        self.cell_text_right = []

        # puzzle info
        self.current_cages = None
        self.current_n = 0

        # CA state
        self.stop_ca = False
        self.last_ca_time = 0.0
        self.last_ca_gens = 0

        # BT animation state
        self.bt_actions = []
        self.skip_bt_animation = False
        self.bt_steps = 0
        self.bt_time = 0
        self.final_bt_board = None

        # the top UI panel

        top = tk.Frame(root)
        top.pack(pady=10)

        # puzzle selection
        ttk.Label(top, text="Choose Puzzle:").grid(row=0, column=0, padx=5)
        self.puzzle_var = tk.StringVar(value=list(PUZZLES.keys())[0])
        self.dropdown_puzzles = ttk.Combobox(
            top, textvariable=self.puzzle_var,
            values=list(PUZZLES.keys()), width=32
        )
        self.dropdown_puzzles.grid(row=0, column=1, padx=5)
        ttk.Button(top, text="Load Puzzle", command=self.load_puzzle).grid(row=0, column=2, padx=5)

        # algorithm dropdown
        ttk.Label(top, text="Algorithm:").grid(row=1, column=0)
        self.alg_var = tk.StringVar(value="Cultural Algorithm")
        self.alg_dropdown = ttk.Combobox(
            top, textvariable=self.alg_var,
            values=["Cultural Algorithm", "Backtracking"], width=32
        )
        self.alg_dropdown.grid(row=1, column=1)

        # solve button
        self.btn_solve = ttk.Button(top, text="Solve", command=self.solve)
        self.btn_solve.grid(row=1, column=2, padx=5)


        # ca update gen interval

        ttk.Label(top, text="CA Update Interval (Gens):").grid(row=2, column=0)
        self.ca_interval_var = tk.IntVar(value=50)
        self.ca_interval_box = ttk.Combobox(
            top, textvariable=self.ca_interval_var,
            values=[10, 25, 50, 100, 200], width=10
        )
        self.ca_interval_box.grid(row=2, column=1)

        # force stop for CA - needed it for testing long runs ~ youssef241784
        self.btn_stop = ttk.Button(top, text="Force Stop CA", command=self.force_stop_ca)
        self.btn_stop.grid(row=2, column=2, padx=5)
        self.btn_stop.config(state="disabled")

        # comparison mode checkbox
        self.comp_var = tk.BooleanVar(value=False)
        self.chk_compare = ttk.Checkbutton(top, text="Comparison Mode", variable=self.comp_var)
        self.chk_compare.grid(row=3, column=0, columnspan=3, pady=5)

        # skip BT animation button since animation can be long but runtime is much less ~ youssef241784
        self.btn_skip_bt = ttk.Button(top, text="Skip BT Animation",
                                      command=lambda: setattr(self, "skip_bt_animation", True))
        self.btn_skip_bt.grid(row=4, column=0, columnspan=3, pady=5)
        self.btn_skip_bt.config(state="disabled")

        # clear + save buttons
        self.btn_clear = ttk.Button(top, text="Clear", command=self.clear_output)
        self.btn_clear.grid(row=5, column=0, columnspan=3, pady=5)

        self.btn_save = ttk.Button(top, text="Save Result", command=self.save_result)
        self.btn_save.grid(row=6, column=0, columnspan=3, pady=5)

        # status labels
        self.status_label = ttk.Label(root, text="Status: Idle")
        self.status_label.pack()

        self.gen_label = ttk.Label(root, text="Gen: 0 | Fitness: ?")
        self.gen_label.pack()

        # frame that holds both canvases
        self.canvas_frame = tk.Frame(root)
        self.canvas_frame.pack(pady=10)

        # frames to hold CA (left) and BT (right) labels under the canvases
        self.metrics_frame = tk.Frame(root)
        self.metrics_frame.pack(pady=10)

        self.ca_metrics_frame = tk.Frame(self.metrics_frame)
        self.ca_metrics_frame.pack(side="left", padx=80)

        self.bt_metrics_frame = tk.Frame(self.metrics_frame)
        self.bt_metrics_frame.pack(side="right", padx=80)

        # labels for CA and BT metrics
        # left for CA
        self.label_ca_comparison = ttk.Label(self.ca_metrics_frame, text="Cultural Algorithm", font=("Arial", 13, "bold"))
        self.label_ca_gens = ttk.Label(self.ca_metrics_frame, text="")
        self.label_ca_time = ttk.Label(self.ca_metrics_frame, text="")

        #right for BT
        self.label_bt_comparison = ttk.Label(self.bt_metrics_frame, text="Backtracking", font=("Arial", 13, "bold"))
        self.label_bt_steps = ttk.Label(self.bt_metrics_frame, text="")
        self.label_bt_time = ttk.Label(self.bt_metrics_frame, text="")


        self.canvas_frame = tk.Frame(root)
        self.canvas_frame.pack(pady=10)

    # build puzzle canvas function 

    def build_canvas(self, cages, n, side="left"):
        canvas_attr = "canvas_left" if side == "left" else "canvas_right"
        text_attr = "cell_text_left" if side == "left" else "cell_text_right"

        old_canvas = getattr(self, canvas_attr)
        if old_canvas:
            old_canvas.destroy()

        canvas = tk.Canvas(self.canvas_frame, width=n*CELL_SIZE, height=n*CELL_SIZE, bg="white")
        canvas.pack(side="left" if side == "left" else "right", padx=50)
        setattr(self, canvas_attr, canvas)

        cell_ids = [[None]*n for _ in range(n)]
        setattr(self, text_attr, cell_ids)

        # grid
        for i in range(n+1):
            w = 2 if i in (0, n) else 1
            canvas.create_line(0, i*CELL_SIZE, n*CELL_SIZE, i*CELL_SIZE, width=w)
            canvas.create_line(i*CELL_SIZE, 0, i*CELL_SIZE, n*CELL_SIZE, width=w)

        # cage borders
        for cells, _, _ in cages:
            for (r, c) in cells:
                x0, y0 = c*CELL_SIZE, r*CELL_SIZE
                x1, y1 = x0+CELL_SIZE, y0+CELL_SIZE
                if (r-1, c) not in cells: canvas.create_line(x0, y0, x1, y0, width=3)
                if (r+1, c) not in cells: canvas.create_line(x0, y1, x1, y1, width=3)
                if (r, c-1) not in cells: canvas.create_line(x0, y0, x0, y1, width=3)
                if (r, c+1) not in cells: canvas.create_line(x1, y0, x1, y1, width=3)

        # cage labels
        for cells, tgt, op in cages:
            (r, c) = sorted(cells)[0]
            canvas.create_text(c*CELL_SIZE+5, r*CELL_SIZE+5, text=f"{tgt}{op}", anchor="nw", font=FONT_CAGE)

        # cell items that are filled later with (1 to n) numbers
        for r in range(n):
            for c in range(n):
                tid = canvas.create_text(
                    c*CELL_SIZE + CELL_SIZE/2,
                    r*CELL_SIZE + CELL_SIZE/2,
                    text="", font=FONT_NUM
                )
                cell_ids[r][c] = tid

    # load puzzle function

    def load_puzzle(self):
        name = self.puzzle_var.get()
        cages = PUZZLES[name]
        n = max(max(r for r, _ in cage[0]) for cage in cages) + 1

        self.current_cages = cages
        self.current_n = n

        # build CA canvas
        self.build_canvas(cages, n, side="left")
        
        # build BT canvas [for comparison mode]
        if self.comp_var.get():
            self.build_canvas(cages, n, side="right")
            self.label_bt_comparison.pack(padx = 35)
            self.label_ca_comparison.pack(padx = 35)
            self.label_ca_time.pack(padx=35)
            self.label_ca_gens.pack(padx = 35)
            self.label_bt_time.pack(padx = 35)
            self.label_bt_steps.pack(padx = 35)

        else:
            self.label_ca_time.config(text="")
            self.label_ca_gens.config(text="")
            self.label_bt_time.config(text="")
            self.label_bt_steps.config(text="")

        self.status_label.config(text=f"Loaded puzzle: {name}")
        self.gen_label.config(text="Gen: 0 | Fitness: ?")

    # CA live update callback
    def update_canvas_ca(self, grid, fit, gen):
        for r in range(self.current_n):
            for c in range(self.current_n):
                self.canvas_left.itemconfig(self.cell_text_left[r][c], text=str(grid[r][c]))

        self.gen_label.config(text=f"Gen {gen} | Fitness {fit}")
        self.root.update()

        if self.stop_ca:
            raise Exception("CA Force-Stopped")

    # solve functions
   
    def solve(self):
        if self.current_cages is None or self.current_n == 0:
            messagebox.showwarning("No puzzle loaded", "Please load a puzzle before solving.")
            return


        if self.alg_var.get() == "Cultural Algorithm":
            self.solve_ca()
        else:
            self.solve_bt()

    # solve function for CA
    def solve_ca(self):
        self.disable_buttons()
        self.stop_ca = False
        self.gen_label.config(text="")
        self.status_label.config(text="Solving CA")

        cages = self.current_cages
        n = self.current_n
        interval = int(self.ca_interval_var.get())  # <<<< interval restored

        def worker():
            try:
                sol, fit, t, gen = cultural_algorithm(
                    cages, n,
                    gui_callback=self.update_canvas_ca,
                    update_interval=interval,
                    should_stop=lambda: self.stop_ca
                )

                self.last_ca_time = t
                self.last_ca_gens = gen

                # Draw final
                for r in range(n):
                    for c in range(n):
                        self.canvas_left.itemconfig(self.cell_text_left[r][c], text=str(sol[r][c]))

                self.status_label.config(
                    text=f"CA Solved | Time {t:.6f}s | Gens {gen} | Fitness {fit}"
                )

                self.label_ca_time.config(text=f"CA Time: {t:.6f}s")
                self.label_ca_gens.config(text=f"CA Gens: {gen}")

            except Exception as e:
                if "Force-Stopped" in str(e):
                    self.status_label.config(text="CA Stopped by User")
                else:
                    messagebox.showerror("CA Error", str(e))

            self.enable_buttons()

        threading.Thread(target=worker).start()

    # force stop CA
    def force_stop_ca(self):
        self.stop_ca = True

    # solve function for BT
    def solve_bt(self):
        cages = self.current_cages
        n = self.current_n

        self.disable_buttons()
        self.status_label.config(text="")
        self.gen_label.config(text="")
        self.status_label.config(text="Running BT...")
        

        def worker():
            try:
                sol, steps, t, actions = compute_animation_sequence(cages, n)

                self.final_bt_board = sol
                self.bt_steps = steps
                self.bt_time = t
                self.bt_actions = actions[:]
                self.skip_bt_animation = False

                self.btn_skip_bt.config(state="normal")

                if self.comp_var.get():
                    self.label_bt_time.config(text=f"BT Time: {t:.6f}s")
                    self.label_bt_steps.config(text=f"BT Steps: {steps}")

                self.status_label.config(text="Animating BT...")
                self.root.after(10, self.animate_bt_step)

            except Exception as e:
                messagebox.showerror("BT Error", str(e))
                self.enable_buttons()

        threading.Thread(target=worker).start()

    # BT animation loop
    def animate_bt_step(self):
        canvas = self.canvas_left if not self.comp_var.get() else self.canvas_right
        ids = self.cell_text_left if not self.comp_var.get() else self.cell_text_right

        # skip animation immediately
        if self.skip_bt_animation:
            for r in range(self.current_n):
                for c in range(self.current_n):
                    canvas.itemconfig(ids[r][c], text=str(self.final_bt_board[r][c]), fill="black")

            self.status_label.config(
                text=f"BT Solved (Animation Skipped) | Time {self.bt_time:.6f}s | Steps {self.bt_steps}"
            )
            self.btn_skip_bt.config(state="disabled")
            self.enable_buttons()
            return

        # animation end
        if not self.bt_actions:
            self.status_label.config(
                text=f"BT Solved | Time {self.bt_time:.6f}s | Steps {self.bt_steps}"
            )
            self.btn_skip_bt.config(state="disabled")
            self.enable_buttons()
            return

        # perform next animation action
        r, c, val, is_trial = self.bt_actions.pop(0)

        if is_trial:
            canvas.itemconfig(ids[r][c], text=str(val), fill="blue")
        else:
            if val == 0:
                canvas.itemconfig(ids[r][c], text="", fill="red")
            else:
                canvas.itemconfig(ids[r][c], text=str(val), fill="black")

        self.root.after(BT_DELAY, self.animate_bt_step)

    # clear the GUI
    def clear_output(self):
        self.status_label.config(text="Cleared")
        self.gen_label.config(text="Gen: 0 | Fitness: ?")

        if self.canvas_left:
            self.canvas_left.destroy()
            self.canvas_left = None
        if self.canvas_right:
            self.canvas_right.destroy()
            self.canvas_right = None

        self.label_ca_time.config(text="")
        self.label_ca_gens.config(text="")
        self.label_bt_time.config(text="")
        self.label_bt_steps.config(text="")

        self.btn_skip_bt.config(state="disabled")

    # save result to file
    def save_result(self):
        if not self.canvas_left:
            messagebox.showwarning("No result", "Solve a puzzle first.")
            return

        filename = filedialog.asksaveasfilename(
            defaultextension=".txt",
            filetypes=[("Text files", "*.txt"), ("CSV files", "*.csv")]
        )
        if not filename:
            return

        with open(filename, "w") as f:
            f.write(f"Solved on: {datetime.now()}\n")
            f.write(f"Puzzle: {self.puzzle_var.get()}\n")

            # if single algorithm mode
            if not self.comp_var.get():
                alg = self.alg_var.get()
                f.write(f"Algorithm: {alg}\n")

                if alg == "Cultural Algorithm":
                    f.write(f"CA Time: {self.last_ca_time:.6f}s\n")
                    f.write(f"CA Generations: {self.last_ca_gens}\n")

                else:
                    f.write(f"BT Time: {self.bt_time:.6f}s\n")
                    f.write(f"BT Steps: {self.bt_steps}\n")

            # if comparison mode
            else:
                f.write("Algorithm: Comparison Mode\n")
                f.write(f"CA Time: {self.last_ca_time:.6f}s\n")
                f.write(f"CA Generations: {self.last_ca_gens}\n")
                f.write(f"BT Time: {self.bt_time:.6f}s\n")
                f.write(f"BT Steps: {self.bt_steps}\n")

            # solution grid output
            f.write("\nSolution Grid:\n")
            for r in range(self.current_n):
                row_vals = [
                    self.canvas_left.itemcget(self.cell_text_left[r][c], "text")
                    for c in range(self.current_n)
                ]
                f.write(", ".join(row_vals) + "\n")

        messagebox.showinfo("Saved", "Solution exported successfully!")

    # buttons enable & disable functions used during solving
    def disable_buttons(self):
        self.btn_solve.config(state="disabled")
        self.btn_stop.config(state="normal")
        self.btn_clear.config(state="disabled")
        self.btn_save.config(state="disabled")
        self.btn_skip_bt.config(state="disabled")

    def enable_buttons(self):
        self.btn_solve.config(state="normal")
        self.btn_stop.config(state="disabled")
        self.btn_clear.config(state="normal")
        self.btn_save.config(state="normal")


# launch gui function called from main
def launch_gui():
    root = tk.Tk()
    KenKenGUI(root)
    root.mainloop()
