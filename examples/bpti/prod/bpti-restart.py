"""
Description
-----------
Example script of how to run GCMC/MD in OpenMM for a BPTI system, when
restarting from a previous simulation

Note that this simulation is only an example, and is not necessarily long enough
to see equilibrated behaviour

Marley Samways
Ollie Melling
"""

from openmm.app import *
from openmm import *
from openmm.unit import *
from sys import stdout

from openmmtools.integrators import BAOABIntegrator

import grand

# Load in PDB file (for topology)
pdb = PDBFile('bpti-ghosts.pdb')

# Load restart file
rst7 = AmberInpcrdFile('bpti-rst.rst7')

# Shouldn't need to add ghosts as these can just be read in from before (all frames contained below)
ghosts = grand.utils.read_ghosts_from_file('gcmc-ghost-wats.txt')

# Create system
ff = ForceField('amber14-all.xml', 'amber14/tip3p.xml')
system = ff.createSystem(pdb.topology,
                         nonbondedMethod=PME,
                         nonbondedCutoff=12.0*angstroms,
                         switchDistance=10.0*angstroms,
                         constraints=HBonds)

# Define atoms around which the GCMC sphere is based
ref_atoms = [{'name': 'CA', 'resname': 'TYR', 'resid': '10'},
             {'name': 'CA', 'resname': 'ASN', 'resid': '43'}]

gcmc_mover = grand.samplers.StandardGCMCSphereSampler(system=system,
                                                      topology=pdb.topology,
                                                      temperature=298*kelvin,
                                                      ghostFile='gcmc-ghost-wats2.txt',
                                                      referenceAtoms=ref_atoms,
                                                      sphereRadius=4.2*angstroms,
                                                      log='bpti-gcmc2.log',
                                                      dcd='bpti-raw2.dcd',
                                                      rst='bpti-rst2.rst7',
                                                      overwrite=False)

# BAOAB Langevin integrator
integrator = BAOABIntegrator(298*kelvin, 1.0/picosecond, 0.002*picoseconds)

# Define platform and set precision
platform = Platform.getPlatformByName('CUDA')
platform.setPropertyDefaultValue('Precision', 'mixed')

# Create Simulation object
simulation = Simulation(pdb.topology, system, integrator, platform)

# Set positions, velocities and box vectors
simulation.context.setPositions(rst7.getPositions())
simulation.context.setVelocities(rst7.getVelocities())
simulation.context.setPeriodicBoxVectors(*pdb.topology.getPeriodicBoxVectors())

# Make sure the variables are all ready to run & switch of the ghosts from the final frame of the previous run
gcmc_mover.initialise(simulation.context, ghosts[-1])

# Add StateDataReporter for production
simulation.reporters.append(StateDataReporter(stdout,
                                              1000,
                                              step=True,
                                              potentialEnergy=True,
                                              temperature=True,
                                              volume=True))

# Run simulation 
print("\nProduction (continued)")
for i in range(100):
    # Carry out 100 GCMC moves per 1 ps of MD
    simulation.step(1000)
    gcmc_mover.move(simulation.context, 100)
    # Write data out
    gcmc_mover.report(simulation)

#
# Need to process the trajectory for visualisation
#

# Shift ghost waters outside the simulation cell
trj = grand.utils.shift_ghost_waters(ghost_file='gcmc-ghost-wats2.txt',
                                     topology='bpti-ghosts.pdb',
                                     trajectory='bpti-raw2.dcd')

# Centre the trajectory on a particular residue
trj = grand.utils.recentre_traj(t=trj, resname='TYR', resid=10)

# Align the trajectory to the protein
grand.utils.align_traj(t=trj, output='bpti-gcmc2.dcd')

# Write out a PDB trajectory of the GCMC sphere
grand.utils.write_sphere_traj(radius=4.2,
                              ref_atoms=ref_atoms,
                              topology='bpti-ghosts.pdb',
                              trajectory='bpti-gcmc2.dcd',
                              output='gcmc_sphere2.pdb',
                              initial_frame=True)

# Cluster water sites
grand.utils.cluster_waters(topology='bpti-ghosts.pdb',
                           trajectory='bpti-gcmc2.dcd',
                           sphere_radius=4.2,
                           ref_atoms=ref_atoms,
                           cutoff=2.4,
                           output='bpti-clusts.pdb')
