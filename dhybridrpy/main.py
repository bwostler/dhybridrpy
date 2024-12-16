from dhybridrpy import Dhybridrpy
import matplotlib.pyplot as plt
import numpy as np

def main():
    dpy = Dhybridrpy(
        input_file="/project/astroplasmas/bricker/dhybridrpy/examples/data/input/input",
        output_path="/project/astroplasmas/bricker/dhybridrpy/examples/data/Output"
    )

    # print(dpy.inputs)
    # print(dpy.inputs["time"])
    # print(dpy.inputs["diag_species"])
    # print(dpy.timestep(32).fields.Ez(origin="Total").data)
    # ax1 = dpy.timestep(32).fields.Ez().plot(dpi=200, save=True)
    # print(dpy.timestep(32).phases.x3x2x1(species=1).data)
    # tmp = dpy.timestep(32).phases.p3x1().data
    # print(dpy.timestep(32).fields.Bx().plot(save=True))
    # print(dpy.timestep(32).phases.p1x1().plot(save=True))
    # print(dpy.timestep(32).phases.p3x1().data_dict)
    # print(dpy._timesteps_dict[32])

    # Create a composite plot
    fig, axes = plt.subplots(2, 3, figsize=(12, 8))
    
    # Easier to index a flat array
    axes = axes.flatten()

    # Obtain consistent colorbar bounds from field data
    timesteps = dpy.timesteps[1:]
    all_data = [dpy.timestep(ts).fields.Ex().data for ts in timesteps]
    vmin = np.min([np.min(data) for data in all_data])
    vmax = np.max([np.max(data) for data in all_data])

    # Plot field data
    for i, ts in enumerate(timesteps):
        Ex = dpy.timestep(ts).fields.Ex()
        Ex.plot(ax=axes[i], vmin=vmin, vmax=vmax)

    plt.tight_layout()
    plt.savefig("composite_plot.png", dpi=200)

if __name__ == "__main__":
    main()