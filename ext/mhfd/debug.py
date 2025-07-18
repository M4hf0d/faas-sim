#!/usr/bin/env python3
"""
Comprehensive debug script to find the 20-replica scaling limit
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

from sim.faas.core import ScalingConfiguration
from sim.faas.system import DefaultFaasSystem
from sim.core import Environment


# Import your setup
from ext.raith21.main import setup_environment
from ext.raith21.topology import urban_sensing_topology
from ext.raith21.generators.edgegpu import edgegpu_settings
from ext.raith21.resources import ai_resources_per_node_image
from ext.raith21.oracles import Raith21ResourceOracle, Raith21FetOracle
from ext.mhfd.power import Raith21PowerOracle, DEVICE_POWER_PROFILES


def debug_scaling_configuration():
    """Debug ScalingConfiguration class and defaults"""
    print("🔍 DEBUG: ScalingConfiguration Analysis")
    print("=" * 60)
    
    # Check default values
    default_config = ScalingConfiguration()
    print(f"Default ScalingConfiguration:")
    print(f"  scale_min: {default_config.scale_min}")
    print(f"  scale_max: {default_config.scale_max}")
    print(f"  scale_factor: {default_config.scale_factor}")
    print(f"  scale_zero: {default_config.scale_zero}")
    print(f"  rps_threshold: {default_config.rps_threshold}")
    print(f"  target_average_rps: {default_config.target_average_rps}")
    print(f"  target_queue_length: {default_config.target_queue_length}")
    
    # Check class attributes
    print(f"\nClass attributes:")
    for attr in dir(ScalingConfiguration):
        if not attr.startswith('_'):
            value = getattr(ScalingConfiguration, attr)
            if not callable(value):
                print(f"  {attr}: {value}")


def debug_faas_system_constructor():
    """Debug DefaultFaasSystem constructor signature and limits"""
    print("\n🔍 DEBUG: DefaultFaasSystem Constructor")
    print("=" * 60)
    
    import inspect
    sig = inspect.signature(DefaultFaasSystem.__init__)
    print(f"Constructor signature: {sig}")
    
    # Check for any max_replica related attributes
    env = Environment()
    faas = DefaultFaasSystem(env, scale_by_requests=False)
    
    print(f"\nFaasSystem attributes:")
    for attr in dir(faas):
        if 'max' in attr.lower() or 'limit' in attr.lower() or 'replica' in attr.lower():
            value = getattr(faas, attr)
            if not callable(value):
                print(f"  {attr}: {value}")


def debug_scaling_methods():
    """Debug the scale_up method and its logic"""
    print("\n🔍 DEBUG: scale_up Method Analysis")
    print("=" * 60)
    
    import inspect
    
    # Get scale_up method source
    try:
        source = inspect.getsource(DefaultFaasSystem.scale_up)
        print("scale_up method source:")
        print(source)
    except:
        print("Could not retrieve scale_up source")
    
    # Look for hardcoded limits
    if hasattr(DefaultFaasSystem, 'scale_up'):
        print("✅ Found scale_up method")
        # Try to examine the method
        try:
            import dis
            print("\nScale_up method bytecode:")
            dis.dis(DefaultFaasSystem.scale_up)
        except:
            print("Could not disassemble scale_up method")
    else:
        print("❌ No scale_up method found")


def debug_environment_setup():
    """Debug the actual environment setup and find scaling limits"""
    print("\n🔍 DEBUG: Environment Setup Analysis")
    print("=" * 60)    
    
    try:
                # ✅ Fix the topology creation
        from ext.raith21.generators.edgegpu import generate_ether_node_gpu
        from ext.raith21.etherdevices import convert_to_ether_nodes
        
        # Create nodes first
        nodes = convert_to_ether_nodes([
            generate_ether_node_gpu("nuc", "x86", 8, 2, []),
            generate_ether_node_gpu("xeoncpu", "x86", 16, 4, []),
        ])
        
        storage_index = ai_resources_per_node_image()
        topology = urban_sensing_topology(nodes, storage_index)
        
        # Create oracles
        resource_oracle = Raith21ResourceOracle(
            storage_index, 
            edgegpu_settings()
        )
        fet_oracle = Raith21FetOracle(storage_index)
        power_oracle = Raith21PowerOracle(DEVICE_POWER_PROFILES)
        
        # Setup environment
        env = setup_environment(
            topology, 
            storage_index, 
            {}, 
            fet_oracle, 
            resource_oracle, 
            power_oracle
        )
        
        print(f"✅ Environment created successfully")
        # Create minimal environment
        topology = urban_sensing_topology()
        storage_index = ai_resources_per_node_image()
        
        # Create oracles
        resource_oracle = Raith21ResourceOracle(
            storage_index, 
            edgegpu_settings()
        )
        fet_oracle = Raith21FetOracle(storage_index)
        power_oracle = Raith21PowerOracle(DEVICE_POWER_PROFILES)
        
        # Setup environment
        env = setup_environment(
            topology, 
            storage_index, 
            {}, 
            fet_oracle, 
            resource_oracle, 
            power_oracle
        )
        
        print(f"✅ Environment created successfully")
        
        # Debug FaaS system
        print(f"\nFaaS System Type: {type(env.faas)}")
        print(f"Scale by requests: {getattr(env.faas, 'scale_by_requests', 'N/A')}")
        
        # Check all FaaS attributes for limits
        print(f"\nAll FaaS attributes containing 'max', 'limit', or 'replica':")
        for attr in sorted(dir(env.faas)):
            if any(word in attr.lower() for word in ['max', 'limit', 'replica', 'scale']):
                try:
                    value = getattr(env.faas, attr)
                    if not callable(value):
                        print(f"  {attr}: {value}")
                except:
                    print(f"  {attr}: <unable to access>")
        
        # Debug deployments
        print(f"\nFunction Deployments:")
        deployments = env.faas.get_deployments()
        for deployment in deployments:
            print(f"  Function: {deployment.name}")
            print(f"    scale_min: {deployment.scaling_config.scale_min}")
            print(f"    scale_max: {deployment.scaling_config.scale_max}")
            print(f"    scale_factor: {deployment.scaling_config.scale_factor}")
            print(f"    rps_threshold: {deployment.scaling_config.rps_threshold}")
            print(f"    target_average_rps: {deployment.scaling_config.target_average_rps}")
            
        # Debug replica counts
        print(f"\nCurrent Replica Counts:")
        for name, count in env.faas.replica_count.items():
            print(f"  {name}: {count} replicas")
        
        # Debug scalers
        print(f"\nActive Scalers:")
        if hasattr(env.faas, 'faas_scalers'):
            print(f"  FaasRequestScalers: {len(env.faas.faas_scalers)}")
            for name, scaler in env.faas.faas_scalers.items():
                print(f"    {name}: {type(scaler)}")
        
        if hasattr(env.faas, 'avg_faas_scalers'):
            print(f"  AverageFaasRequestScalers: {len(env.faas.avg_faas_scalers)}")
        
        if hasattr(env.faas, 'queue_faas_scalers'):
            print(f"  QueueFaasRequestScalers: {len(env.faas.queue_faas_scalers)}")
        
        # Debug autoscaler
        print(f"\nBackground Processes:")
        for i, process in enumerate(env.background_processes):
            print(f"  Process {i}: {process}")
            if hasattr(process, '__name__'):
                print(f"    Name: {process.__name__}")
            if 'autoscaler' in str(process).lower():
                print(f"    *** AUTOSCALER FOUND ***")
        
        return env
        
    except Exception as e:
        print(f"❌ Environment setup failed: {e}")
        import traceback
        traceback.print_exc()
        return None


def debug_scheduler_limits(env):
    """Debug scheduler for any replica limits"""
    print("\n🔍 DEBUG: Scheduler Limits")
    print("=" * 60)
    
    if not env:
        print("❌ No environment provided")
        return
    
    # Debug scheduler
    scheduler = env.scheduler
    print(f"Scheduler type: {type(scheduler)}")
    
    # Check scheduler attributes
    print(f"Scheduler attributes:")
    for attr in sorted(dir(scheduler)):
        if any(word in attr.lower() for word in ['max', 'limit', 'replica', 'capacity']):
            try:
                value = getattr(scheduler, attr)
                if not callable(value):
                    print(f"  {attr}: {value}")
            except:
                print(f"  {attr}: <unable to access>")


def debug_node_capacities(env):
    """Debug node capacities that might limit scaling"""
    print("\n🔍 DEBUG: Node Capacities")
    print("=" * 60)
    
    if not env:
        print("❌ No environment provided")
        return
    
    # Debug topology nodes
    nodes = env.topology.get_nodes()
    print(f"Total nodes: {len(nodes)}")
    
    # Sample first 5 nodes
    for i, node in enumerate(nodes[:5]):
        print(f"\nNode {i}: {node.name}")
        
        # Check node attributes
        for attr in ['capacity', 'resources', 'max_pods', 'max_replicas']:
            if hasattr(node, attr):
                value = getattr(node, attr)
                print(f"  {attr}: {value}")
        
        # Check skippy node if available
        if hasattr(env, 'cluster') and env.cluster:
            try:
                skippy_node = env.cluster.get_node(node.name)
                if skippy_node and hasattr(skippy_node, 'capacity'):
                    print(f"  skippy_capacity: {skippy_node.capacity}")
                if skippy_node and hasattr(skippy_node, 'allocatable'):
                    print(f"  skippy_allocatable: {skippy_node.allocatable}")
            except:
                pass


def simulate_scaling_attempt(env):
    """Try to manually scale beyond 20 and see what happens"""
    print("\n🔍 DEBUG: Manual Scaling Test")
    print("=" * 60)
    
    if not env:
        print("❌ No environment provided")
        return
    
    # Get first deployment
    deployments = env.faas.get_deployments()
    if not deployments:
        print("❌ No deployments found")
        return
    
    deployment = deployments[0]
    function_name = deployment.name
    
    print(f"Testing scaling for: {function_name}")
    print(f"Current replica count: {env.faas.replica_count.get(function_name, 0)}")
    print(f"Deployment scale_max: {deployment.scaling_config.scale_max}")
    
    # Try to scale to exactly 20
    print(f"\n🧪 Scaling to 20 replicas...")
    original_count = env.faas.replica_count.get(function_name, 0)
    target_count = 20
    scale_amount = target_count - original_count
    
    if scale_amount > 0:
        print(f"Calling faas.scale_up({function_name}, {scale_amount})")
        try:
            # We need to run this as a generator
            scale_gen = env.faas.scale_up(function_name, scale_amount)
            # Run the generator to completion
            list(scale_gen)  # Convert generator to list to execute it
            
            new_count = env.faas.replica_count.get(function_name, 0)
            print(f"Result: {new_count} replicas (expected: {target_count})")
            
            if new_count < target_count:
                print(f"❌ SCALING STOPPED at {new_count} replicas!")
                print(f"❌ UNABLE TO REACH {target_count} replicas!")
                
                # Debug why it stopped
                print(f"\n🔍 DEBUGGING WHY SCALING STOPPED:")
                print(f"  Deployment scale_max: {deployment.scaling_config.scale_max}")
                print(f"  Current replica_count: {env.faas.replica_count.get(function_name, 0)}")
                
                # Check scheduler queue
                if hasattr(env.faas, 'scheduler_queue'):
                    print(f"  Scheduler queue size: {len(env.faas.scheduler_queue.items)}")
                
            else:
                print(f"✅ Successfully reached {target_count} replicas")
                
        except Exception as e:
            print(f"❌ Scaling failed with error: {e}")
            import traceback
            traceback.print_exc()
    
    # Try to scale beyond 20
    print(f"\n🧪 Attempting to scale to 25 replicas...")
    target_count = 25
    current_count = env.faas.replica_count.get(function_name, 0)
    scale_amount = target_count - current_count
    
    if scale_amount > 0:
        print(f"Calling faas.scale_up({function_name}, {scale_amount})")
        try:
            scale_gen = env.faas.scale_up(function_name, scale_amount)
            list(scale_gen)  # Execute the generator
            
            new_count = env.faas.replica_count.get(function_name, 0)
            print(f"Result: {new_count} replicas (expected: {target_count})")
            
            if new_count < target_count:
                print(f"❌ SCALING STOPPED at {new_count} replicas!")
                print(f"❌ CONFIRMED: Cannot scale beyond {new_count} replicas!")
            else:
                print(f"✅ Successfully reached {target_count} replicas")
                
        except Exception as e:
            print(f"❌ Scaling failed with error: {e}")


def main():
    """Run all debug functions"""
    print("🚀 COMPREHENSIVE SCALING LIMITS DEBUG")
    print("=" * 80)
    
    # 1. Debug ScalingConfiguration
    debug_scaling_configuration()
    
    # 2. Debug FaaS system constructor
    debug_faas_system_constructor()
    
    # 3. Debug scaling methods
    debug_scaling_methods()
    
    # 4. Debug environment setup
    env = debug_environment_setup()
    
    # 5. Debug scheduler
    debug_scheduler_limits(env)
    
    # 6. Debug node capacities
    debug_node_capacities(env)
    
    # 7. Test manual scaling
    simulate_scaling_attempt(env)
    
    print("\n" + "=" * 80)
    print("✅ DEBUG ANALYSIS COMPLETE")
    print("=" * 80)


if __name__ == "__main__":
    main()