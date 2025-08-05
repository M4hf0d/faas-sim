from ext.raith21.generators.edgesbc import edgesbc_settings
from ext.raith21.generator import GeneratorSettings, Arch
from ext.raith21.device import ArchProperties
from ext.raith21.model import *
import copy
import logging

logger = logging.getLogger(__name__)


def make_edgeai_settings(num_devices, n_nuc):
    """
    Custom EdgeAI settings with specific device distribution:
    - 0% Xeon (GPU/CPU) 
    - 2 Intel NUC (fixed number)
    - 30% RPi (3 & 4) 
    - 20% RockPi
    - 10% Nano
    - 10% NX  
    - 5% Coral
    Remaining percentage adjusts other AARCH64 devices (TX2, etc.)
    """
    settings = copy.deepcopy(edgesbc_settings)
    
    # Calculate percentages
    nuc_percentage = n_nuc / num_devices  # Fixed NUC count
    rpi_percentage = 0.30    # 30% RPi
    rockpi_percentage = 0.20 # 20% RockPi  
    nano_percentage = 0.10   # 10% Nano
    nx_percentage = 0.10     # 10% NX
    coral_percentage = 0.05  # 5% Coral
    
    # Total AARCH64 percentage
    aarch64_percentage = rockpi_percentage + nano_percentage + nx_percentage + coral_percentage
    
    # Set architecture distributions
    settings.arch[Arch.X86] = nuc_percentage      # Only Intel NUC
    settings.arch[Arch.ARM32] = rpi_percentage    # RPi 3 & 4
    settings.arch[Arch.AARCH64] = aarch64_percentage  # RockPi, Nano, NX, Coral
    
    # Verify percentages sum to ~1.0
    total_percentage = nuc_percentage + rpi_percentage + aarch64_percentage
    if abs(total_percentage - 1.0) > 0.01:
        logger.warning(f"⚠️  Percentages don't sum to 1.0: {total_percentage:.3f}")
        # Adjust AARCH64 to balance
        settings.arch[Arch.AARCH64] = 1.0 - nuc_percentage - rpi_percentage
    
    # X86 properties (Intel NUC only - no Xeon)
    settings.properties[Arch.X86] = ArchProperties(
        arch=Arch.X86,
        accelerator={Accelerator.NONE: 1.0, Accelerator.GPU: 0.0, Accelerator.TPU: 0.0},
        cores={Bins.LOW: 0.0, Bins.MEDIUM: 1.0, Bins.HIGH: 0.0, Bins.VERY_HIGH: 0.0},
        location={Location.EDGE: 1.0, Location.CLOUD: 0.0, Location.MEC: 0.0, Location.MOBILE: 0.0},
        connection={Connection.ETHERNET: 0.0, Connection.WIFI: 0.0, Connection.MOBILE: 1.0},
        network={Bins.LOW: 1.0, Bins.MEDIUM: 0.0, Bins.HIGH: 0.0, Bins.VERY_HIGH: 0.0},
        cpu_mhz={Bins.LOW: 0.0, Bins.MEDIUM: 1.0, Bins.HIGH: 0.0, Bins.VERY_HIGH: 0.0},
        cpu={CpuModel.I7: 1.0, CpuModel.XEON: 0.0},  # No Xeon
        ram={Bins.LOW: 0.0, Bins.MEDIUM: 0.0, Bins.HIGH: 1.0, Bins.VERY_HIGH: 0.0},
        disk={Disk.NVME: 1.0, Disk.SSD: 0.0, Disk.SD: 0.0, Disk.FLASH: 0.0, Disk.HDD: 0.0},
        gpu_vram={},  # No GPU
        gpu_model={},
        gpu_mhz={},
    )
    
    # ARM32 properties (RPi 3 & 4)
    settings.properties[Arch.ARM32] = ArchProperties(
        arch=Arch.ARM32,
        accelerator={Accelerator.NONE: 1.0, Accelerator.GPU: 0.0, Accelerator.TPU: 0.0},
        cores={Bins.LOW: 1.0, Bins.MEDIUM: 0.0, Bins.HIGH: 0.0, Bins.VERY_HIGH: 0.0},  # Low cores
        location={Location.EDGE: 1.0, Location.CLOUD: 0.0, Location.MEC: 0.0, Location.MOBILE: 0.0},
        connection={Connection.WIFI: 1.0, Connection.ETHERNET: 0.0, Connection.MOBILE: 0.0},
        network={Bins.LOW: 1.0, Bins.MEDIUM: 0.0, Bins.HIGH: 0.0, Bins.VERY_HIGH: 0.0},
        cpu_mhz={Bins.LOW: 1.0, Bins.MEDIUM: 0.0, Bins.HIGH: 0.0, Bins.VERY_HIGH: 0.0},
        cpu={CpuModel.ARM: 1.0},
        ram={Bins.LOW: 1.0, Bins.MEDIUM: 0.0, Bins.HIGH: 0.0, Bins.VERY_HIGH: 0.0},  # 1GB
        disk={Disk.SD: 1.0, Disk.SSD: 0.0, Disk.NVME: 0.0, Disk.FLASH: 0.0, Disk.HDD: 0.0},
        gpu_vram={},
        gpu_model={},
        gpu_mhz={},
    )
    
    # AARCH64 properties (RockPi, Nano, NX, Coral, TX2)
    # This will be distributed among the different AARCH64 devices
    total_aarch64_devices = rockpi_percentage + nano_percentage + nx_percentage + coral_percentage
    
    # Calculate relative proportions within AARCH64
    if total_aarch64_devices > 0:
        rockpi_ratio = rockpi_percentage / total_aarch64_devices  # ~0.44 (20/45)
        nano_ratio = nano_percentage / total_aarch64_devices      # ~0.22 (10/45)  
        nx_ratio = nx_percentage / total_aarch64_devices          # ~0.22 (10/45)
        coral_ratio = coral_percentage / total_aarch64_devices    # ~0.11 (5/45)
        # TX2 gets the remaining (if any)
        tx2_ratio = max(0.0, 1.0 - rockpi_ratio - nano_ratio - nx_ratio - coral_ratio)
    else:
        rockpi_ratio = nano_ratio = nx_ratio = coral_ratio = tx2_ratio = 0.2
    
    settings.properties[Arch.AARCH64] = ArchProperties(
        arch=Arch.AARCH64,
        accelerator={
            Accelerator.NONE: rockpi_ratio,                    # RockPi (no accelerator)
            Accelerator.GPU: nano_ratio + nx_ratio + tx2_ratio, # Nano + NX + TX2 (GPU)
            Accelerator.TPU: coral_ratio                       # Coral (TPU)
        },
        cores={Bins.LOW: 0.0, Bins.MEDIUM: 1.0, Bins.HIGH: 0.0, Bins.VERY_HIGH: 0.0},
        location={Location.EDGE: 1.0, Location.CLOUD: 0.0, Location.MEC: 0.0, Location.MOBILE: 0.0},
        connection={Connection.WIFI: 0.8, Connection.ETHERNET: 0.2, Connection.MOBILE: 0.0},
        network={Bins.LOW: 0.6, Bins.MEDIUM: 0.4, Bins.HIGH: 0.0, Bins.VERY_HIGH: 0.0},
        cpu_mhz={Bins.LOW: 0.3, Bins.MEDIUM: 0.7, Bins.HIGH: 0.0, Bins.VERY_HIGH: 0.0},
        cpu={CpuModel.ARM: 1.0},
        ram={Bins.LOW: coral_ratio, Bins.MEDIUM: rockpi_ratio + nano_ratio, Bins.HIGH: nx_ratio + tx2_ratio, Bins.VERY_HIGH: 0.0},
        gpu_vram={Bins.LOW: 0.0, Bins.MEDIUM: 1.0, Bins.HIGH: 0.0, Bins.VERY_HIGH: 0.0},
        gpu_model={
            GpuModel.MAXWELL: nano_ratio / (nano_ratio + nx_ratio + tx2_ratio) if (nano_ratio + nx_ratio + tx2_ratio) > 0 else 0.0,  # Nano
            GpuModel.VOLTA: nx_ratio / (nano_ratio + nx_ratio + tx2_ratio) if (nano_ratio + nx_ratio + tx2_ratio) > 0 else 0.0,     # NX
            GpuModel.PASCAL: tx2_ratio / (nano_ratio + nx_ratio + tx2_ratio) if (nano_ratio + nx_ratio + tx2_ratio) > 0 else 0.0,   # TX2
            GpuModel.TURING: 0.0
        },
        gpu_mhz={Bins.LOW: 0.0, Bins.MEDIUM: 1.0, Bins.HIGH: 0.0, Bins.VERY_HIGH: 0.0},
        disk={Disk.SD: 0.6, Disk.FLASH: 0.4, Disk.SSD: 0.0, Disk.NVME: 0.0, Disk.HDD: 0.0},
    )
    
    # Log the expected distribution
    logger.info(f"🏭 Custom EdgeAI Distribution (for {num_devices} devices):")
    logger.info(f"  X86 (NUC): {nuc_percentage:.1%} ({n_nuc} devices)")
    logger.info(f"  ARM32 (RPi): {rpi_percentage:.1%} ({int(num_devices * rpi_percentage)} devices)")
    logger.info(f"  AARCH64 total: {aarch64_percentage:.1%}")
    logger.info(f"    - RockPi: ~{rockpi_percentage:.1%} ({int(num_devices * rockpi_percentage)} devices)")
    logger.info(f"    - Nano: ~{nano_percentage:.1%} ({int(num_devices * nano_percentage)} devices)")
    logger.info(f"    - NX: ~{nx_percentage:.1%} ({int(num_devices * nx_percentage)} devices)")
    logger.info(f"    - Coral: ~{coral_percentage:.1%} ({int(num_devices * coral_percentage)} devices)")
    if tx2_ratio > 0:
        tx2_percentage = aarch64_percentage * tx2_ratio
        logger.info(f"    - TX2: ~{tx2_percentage:.1%} ({int(num_devices * tx2_percentage)} devices)")
    
    return settings