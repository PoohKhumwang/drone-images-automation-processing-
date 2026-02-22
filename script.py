from pydoc import doc
import Metashape
import tkinter as tk
from tkinter import filedialog, messagebox
import os


# =========================
# GUI Functions
# =========================


def step1_before_gcp():
    global output_folder, folder_name, image_folder, gcp_folder, project_path
    root.withdraw()

    folder = filedialog.askdirectory(title="Select Photo Folder")
    root.deiconify()
    folder_name = os.path.basename(folder)
    image_folder = os.path.join(folder, "Original")
    output_folder = os.path.join(folder, "Output")
    gcp_folder = os.path.join(folder, "Processing")
    project_path = os.path.join(gcp_folder, folder_name + ".psx")

    gcp_file = os.path.join(
        gcp_folder,
        [f for f in os.listdir(gcp_folder) if f.endswith(".csv")][0],
    )
    doc = Metashape.app.document
    chunk = doc.chunk

    # Load photos
    photos = [
        os.path.join(image_folder, f)
        for f in os.listdir(image_folder)
        if f.lower().endswith(".jpg")
    ]

    chunk.addPhotos(photos, load_reference=True)
    chunk.matchPhotos(
        downscale=1,
        generic_preselection=True,
        reference_preselection=True,
        reference_preselection_mode=Metashape.ReferencePreselectionMode.ReferencePreselectionSource,
    )
    chunk.alignCameras()

    # ---- LOCK camera references (VERY IMPORTANT) ----
    for cam in chunk.cameras:
        cam.reference.enabled = False

    chunk.importReference(
        path=gcp_file,
        format=Metashape.ReferenceFormatCSV,
        columns="nxyz",
        delimiter=",",
        ignore_labels=False,
        create_markers=True,
    )
    messagebox.showinfo(
        "Step 1 Done",
        "✔ Photos aligned\n"
        "✔ GCP list imported\n\n"
        "👉 Now manually mark GCPs in Metashape.\n"
        "When finished, run Step 2.",
    )
    return folder_name, output_folder


def step2_after_gcp():
    global output_folder, folder_name, image_folder, project_path
    doc = Metashape.app.document
    chunk = doc.chunk
    # project_path = os.path.join(gcp_folder, folder_name + ".psx")
    # Metashape.app.getSaveFileName
    # if not chunk:
    #     messagebox.showerror("Error", "No chunk found.")
    #     return

    root.withdraw()

    # Update transform after manual GCP marking
    chunk.updateTransform()

    # Optimize
    chunk.optimizeCameras()
    # Continue processing
    chunk.buildDepthMaps(downscale=1, filter_mode=Metashape.AggressiveFiltering)
    chunk.buildDenseCloud()
    doc.save(project_path)
    doc.clear()
    doc.open(project_path)
    chunk = doc.chunk

    chunk.buildDem(
        source_data=Metashape.DataSource.DenseCloudData,
        interpolation=Metashape.Interpolation.EnabledInterpolation,
    )
    doc.save()

    chunk.buildOrthomosaic(surface_data=Metashape.ElevationData)
    # doc.save(project_path)
    # Export results
    chunk.exportRaster(
        path=os.path.join(output_folder, folder_name + "_orthomosaic_10cm_48N.tif"),
        image_format=Metashape.ImageFormatTIFF,
        resolution=0.1,
    )
    chunk.exportRaster(
        path=os.path.join(output_folder, folder_name + "_orthomosaic_10cm_48N.jpg"),
        image_format=Metashape.ImageFormatPNG,
        resolution=0.1,
    )
    chunk.exportRaster(
        path=os.path.join(output_folder, folder_name + "_orthomosaic_50cm_48N.tif"),
        image_format=Metashape.ImageFormatTIFF,
        resolution=0.5,
    )
    chunk.exportRaster(
        path=os.path.join(output_folder, folder_name + "_orthomosaic_50cm_48N.jpg"),
        image_format=Metashape.ImageFormatPNG,
        resolution=0.5,
    )

    messagebox.showinfo("Done", "Processing completed!")


# =========================
# GUI Window
# =========================

root = tk.Tk()
root.title("Metashape Manual GCP Workflow")
root.geometry("350x150")

tk.Label(root, text="Manual GCP Workflow", font=("Arial", 14, "bold")).pack(pady=10)

tk.Button(
    root,
    text="Step 1: Align + Load GCPs",
    bg="lightblue",
    command=step1_before_gcp,
    width=30,
).pack(pady=5)

tk.Button(
    root,
    text="Step 2: Process After Marking GCPs",
    bg="lightgreen",
    command=step2_after_gcp,
    width=30,
).pack(pady=5)

root.mainloop()
