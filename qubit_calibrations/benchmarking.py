from . import calibrated_readout
from .. import clifford
from .. import interleaved_benchmarking
from . import Ramsey
from . import excitation_pulse
from . import channel_amplitudes
import numpy as np

def benchmarking_pi2(self, device, qubit_id, *params, pause_length=0, random_sequence_num=20, seq_lengths_num=20):
    coherence_measurement = Ramsey.get_Ramsey_coherence_measurement(device, qubit_id)
    T2 = float(coherence_measurement.metadata['decay'])
    pi2_pulse = excitation_pulse.get_excitation_pulse(device, qubit_id, np.pi/2.)
    pi2_pulse_length = float(pi2_pulse.metadata['length'])
    channel_amplitudes_ = channel_amplitudes.channel_amplitudes(
        device.exdir_db.select_measurement_by_id(pi2_pulse.references['channel_amplitudes']))
    max_pulses = T2/pi2_pulse_length
    seq_lengths = np.round(np.linspace(0, max_pulses, seq_lengths_num))

    def get_pulse_seq_z(z_phase):
        pg = device.pg
        z_pulse = [(c, device.pg.vz, z_phase) for c, a in channel_amplitudes_.items()]
        sequence_z = [pg.pmulti(0, *tuple(z_pulse))]
        return sequence_z

    qubit_readout_pulse, readout_device = calibrated_readout.get_calibrated_measurer(device, [qubit_id])
    HZ = {'H': {
        'pulses': self.get_pulse_seq_z(np.pi / 2) + pi2_pulse.get_pulse_sequence(np.pi) + self.get_pulse_seq_z(
            np.pi / 2),
        'unitary': np.sqrt(0.5) * np.asarray([[1, 1], [1, -1]])},
          'Z': {'pulses': self.get_pulse_seq_z(np.pi),
                'unitary': np.asarray([[1, 0], [0, -1]])},
          'Z/2': {'pulses': self.get_pulse_seq_z(np.pi / 2),
                  'unitary': np.asarray([[1, 0], [0, 1j]])},
          '-Z/2': {'pulses': self.get_pulse_seq_z(-np.pi / 2.),
                   'unitary': np.asarray([[1, 0], [0, -1j]])},
          'I': {'pulses': [], 'unitary': np.asarray([[1, 0], [0, 1]])}
          }

    HZ_group = clifford.generate_group(HZ)

    ro_seq = device.pg.pmulti(pause_length)+device.trigger_readout_seq+qubit_readout_pulse
    pi2_bench = interleaved_benchmarking.interleaved_benchmarking(readout_device,
            set_seq = lambda x: device.pg.set_seq(x+ro_seq))

    pi2_bench.interleavers = HZ_group

    pi2_bench.random_sequence_num = random_sequence_num
    random_sequence_ids = np.arange(self.pi2_bench.random_sequence_num)

    pi2_bench.prepare_random_interleaving_sequences()
    clifford_bench = device.sweeper.sweep(pi2_bench,
                                    (seq_lengths, pi2_bench.set_sequence_length_and_regenerate, 'Gate number', ''),
                                    *params,
                                    (random_sequence_ids, pi2_bench.set_interleaved_sequence, 'Random sequence id', ''),
                                    measurement_type='pi2_bench',
                                    metadata={'qubit_id':qubit_id}, references={'pi2_pulse':pi2_pulse.id})
    return clifford_bench