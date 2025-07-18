from dataclasses import dataclass
from typing import Dict

from ext.raith21 import images, storage
from sim.faas import (
    DeploymentRanking,
    FunctionDeployment,
    FunctionImage,
    FunctionContainer,
    KubernetesResourceConfiguration,
    Function,
    ScalingConfiguration,
)
from sim.oracle.oracle import ResourceOracle, FetOracle

default_resnet_inference_ranking = DeploymentRanking(
    [images.resnet50_inference_gpu_manifest, images.resnet50_inference_cpu_manifest]
)
default_speech_inference_ranking = DeploymentRanking(
    [images.speech_inference_tflite_manifest, images.speech_inference_gpu_manifest]
)
default_mobilenet_inference_ranking = DeploymentRanking(
    [
        images.mobilenet_inference_tpu_manifest,
        images.mobilenet_inference_tflite_manifest,
    ]
)
default_resnet_training_ranking = DeploymentRanking(
    [images.resnet50_training_gpu_manifest, images.resnet50_training_cpu_manifest]
)
default_pi_ranking = DeploymentRanking([images.pi_manifest])
default_fio_ranking = DeploymentRanking([images.fio_manifest])
default_tf_gpu_ranking = DeploymentRanking([images.tf_gpu_manifest])
default_resnet_preprocessing_ranking = DeploymentRanking(
    [images.resnet50_preprocessing_manifest]
)

# ADD NEW SMART CITY FUNCTION RANKINGS HERE:
default_video_analytics_ranking = DeploymentRanking([images.video_analytics_manifest])
default_iot_data_processor_ranking = DeploymentRanking([images.iot_data_processor_manifest])
default_alert_service_ranking = DeploymentRanking([images.alert_service_manifest])
default_data_aggregator_ranking = DeploymentRanking([images.data_aggregator_manifest])

@dataclass
class DeploymentSettings:
    resnet_inference_ranking: DeploymentRanking = default_resnet_inference_ranking
    resnet_preprocessing_ranking: DeploymentRanking = (
        default_resnet_preprocessing_ranking
    )
    speech_inference_ranking: DeploymentRanking = default_speech_inference_ranking
    mobilenet_inference_ranking: DeploymentRanking = default_mobilenet_inference_ranking
    resnet_training_ranking: DeploymentRanking = default_resnet_training_ranking
    tf_gpu_ranking: DeploymentRanking = default_tf_gpu_ranking
    pi_ranking: DeploymentRanking = default_pi_ranking
    fio_ranking: DeploymentRanking = default_fio_ranking
    # ADD NEW SMART CITY RANKINGS:
    video_analytics_ranking: DeploymentRanking = default_video_analytics_ranking
    iot_data_processor_ranking: DeploymentRanking = default_iot_data_processor_ranking
    alert_service_ranking: DeploymentRanking = default_alert_service_ranking
    data_aggregator_ranking: DeploymentRanking = default_data_aggregator_ranking


def get_resnet50_inference_deployment(
    ranking: DeploymentRanking, scaling_config: ScalingConfiguration = None
) -> FunctionDeployment:
    # Design Time
    resnet50_cpu_function_image = FunctionImage(
        image=images.resnet50_inference_cpu_manifest
    )
    resnet50_gpu_function_image = FunctionImage(
        image=images.resnet50_inference_gpu_manifest
    )

    resnet50_function = Function(
        images.resnet50_inference_function,
        fn_images=[resnet50_gpu_function_image, resnet50_cpu_function_image],
    )

    # Run time
    model = storage.resnet_model_bucket_item.name
    data_storage = {
        "data.skippy.io/receives-from-storage": "103M",
        "data.skippy.io/receives-from-storage/path": f"{storage.resnet_model_bucket}/{model}",
    }

    resnet50_cpu_function_requests = KubernetesResourceConfiguration.create_from_str(
        cpu="1000m", memory="150Mi"
    )
    resnet50_cpu_function = FunctionContainer(
        resnet50_cpu_function_image,
        resource_config=resnet50_cpu_function_requests,
        labels={"watchdog": "http", "workers": "4", "cluster": "4a"},
    )

    resnet50_gpu_function_requests = KubernetesResourceConfiguration.create_from_str(
        cpu="1000m", memory="400Mi"
    )
    resnet50_gpu_function = FunctionContainer(
        resnet50_gpu_function_image,
        resource_config=resnet50_gpu_function_requests,
        labels={
            "watchdog": "http",
            "workers": "4",
            "device.edgerun.io/accelerator": "GPU",
            "device.edgerun.io/vram": "1500",
            "cluster": "4b",
        },
    )

    resnet50_gpu_function.labels.update(data_storage)
    resnet50_cpu_function.labels.update(data_storage)

    deployment = FunctionDeployment(
        resnet50_function,
        [resnet50_gpu_function, resnet50_cpu_function],
        ScalingConfiguration() if scaling_config is None else scaling_config,
        ranking,
    )

    return deployment


def get_speech_inference_deployment(
    ranking: DeploymentRanking, scaling_config: ScalingConfiguration = None
) -> FunctionDeployment:
    # Design time
    speech_gpu_function_image = FunctionImage(
        image=images.speech_inference_gpu_manifest
    )
    speech_tflite_function_image = FunctionImage(
        image=images.speech_inference_tflite_manifest
    )
    speech_function = Function(
        images.speech_inference_function,
        fn_images=[speech_gpu_function_image, speech_tflite_function_image],
    )

    # Run time
    tflite = storage.speech_model_tflite_bucket_item
    data_storage_tflite = {
        "data.skippy.io/receives-from-storage": "48M",
        "data.skippy.io/receives-from-storage/path": f"{storage.speech_bucket}/{tflite.name}",
    }
    gpu = storage.speech_model_gpu_bucket_item
    data_storage_gpu = {
        # this size is without scorer object, which is used to impove accuracy but doesn't seem to affect runtime,
        # scorer weighs around 900M - simple benchmarks in bash have made no difference in runtime
        "data.skippy.io/receives-from-storage": "188M",
        "data.skippy.io/receives-from-storage/path": f"{storage.speech_bucket}/{gpu.name}",
    }

    speech_gpu_function_requests = KubernetesResourceConfiguration.create_from_str(
        cpu="1000m", memory="300Mi"
    )
    speech_gpu_function = FunctionContainer(
        speech_gpu_function_image,
        resource_config=speech_gpu_function_requests,
        labels={
            "watchdog": "http",
            "workers": "4",
            "cluster": "0",
            "device.edgerun.io/accelerator": "GPU",
            "device.edgerun.io/vram": "1500",
        },
    )
    speech_gpu_function.labels.update(data_storage_gpu)

    speech_tflite_function_requests = KubernetesResourceConfiguration.create_from_str(
        cpu="1000m", memory="100Mi"
    )
    speech_tflite_function = FunctionContainer(
        speech_tflite_function_image,
        resource_config=speech_tflite_function_requests,
        labels={"watchdog": "http", "workers": "4", "cluster": "1"},
    )
    speech_tflite_function.labels.update(data_storage_tflite)

    deployment = FunctionDeployment(
        speech_function,
        [speech_gpu_function, speech_tflite_function],
        ScalingConfiguration() if scaling_config is None else scaling_config,
        ranking,
    )

    return deployment


def get_mobilenet_inference_deployment(
    ranking: DeploymentRanking, scaling_config: ScalingConfiguration = None
) -> FunctionDeployment:
    # Design time
    mobilenet_tpu_function_image = FunctionImage(
        image=images.mobilenet_inference_tpu_manifest
    )

    mobilenet_tflite_function_image = FunctionImage(
        image=images.mobilenet_inference_tflite_manifest
    )

    mobilenet_function = Function(
        images.mobilenet_inference_function,
        fn_images=[mobilenet_tpu_function_image, mobilenet_tflite_function_image],
    )

    # Run time
    tflite = storage.mobilenet_model_tflite_bucket_item.name
    data_storage_tflite_labels = {
        "data.skippy.io/receives-from-storage": "4M",
        "data.skippy.io/receives-from-storage/path": f"{storage.mobilenet_bucket}/{tflite}",
    }

    tpu = storage.mobilenet_model_tpu_bucket_item.name
    data_storage_tpu_labels = {
        "data.skippy.io/receives-from-storage": "4M",
        "data.skippy.io/receives-from-storage/path": f"{storage.mobilenet_bucket}/{tpu}",
    }

    mobilenet_tpu_function_requests = KubernetesResourceConfiguration.create_from_str(
        cpu="1000m", memory="100Mi"
    )
    mobilenet_tpu_function = FunctionContainer(
        mobilenet_tpu_function_image,
        resource_config=mobilenet_tpu_function_requests,
        labels={
            "watchdog": "http",
            "workers": "4",
            "cluster": "1b",
            "device.edgerun.io/accelerator": "TPU",
        },
    )

    mobilenet_tflite_function_requests = (
        KubernetesResourceConfiguration.create_from_str(cpu="1000m", memory="100Mi")
    )
    mobilenet_tflite_function = FunctionContainer(
        mobilenet_tflite_function_image,
        resource_config=mobilenet_tflite_function_requests,
        labels={"watchdog": "http", "workers": "4", "cluster": "1a"},
    )

    mobilenet_tpu_function.labels.update(data_storage_tpu_labels)
    mobilenet_tflite_function.labels.update(data_storage_tflite_labels)

    deployment = FunctionDeployment(
        mobilenet_function,
        [mobilenet_tpu_function, mobilenet_tflite_function],
        ScalingConfiguration() if scaling_config is None else scaling_config,
        ranking,
    )

    deployment.function_factor = {
        images.mobilenet_inference_tpu_manifest: 1,
        images.mobilenet_inference_tflite_manifest: 1,
    }

    return deployment


def get_resnet_training_deployment(
    ranking: DeploymentRanking, scaling_config: ScalingConfiguration = None
) -> FunctionDeployment:
    # Design Time
    resnet_training_gpu_function_image = FunctionImage(
        image=images.resnet50_training_gpu_manifest
    )

    resnet_training_cpu_function_image = FunctionImage(
        image=images.resnet50_training_cpu_manifest
    )

    resnet_training_function = Function(
        name=images.resnet50_training_function,
        fn_images=[
            resnet_training_gpu_function_image,
            resnet_training_cpu_function_image,
        ],
    )

    # Run time
    resnet_training_gpu_function_requests = (
        KubernetesResourceConfiguration.create_from_str(cpu="1000m", memory="800Mi")
    )
    data = storage.resnet_train_bucket_item.name

    data_storage_labels = {
        "data.skippy.io/receives-from-storage": "58M",
        "data.skippy.io/sends-to-storage": "103M",
        "data.skippy.io/receives-from-storage/path": f"{storage.resnet_train_bucket}/{data}",
        "data.skippy.io/sends-to-storage/path": f"{storage.resnet_train_bucket}/updated_model",
    }

    resnet_training_gpu_function = FunctionContainer(
        resnet_training_gpu_function_image,
        resource_config=resnet_training_gpu_function_requests,
        labels={
            "watchdog": "http",
            "workers": "4",
            "cluster": "2",
            "device.edgerun.io/accelerator": "GPU",
            "device.edgerun.io/vram": "2000",
        },
    )

    resnet_training_gpu_function.labels.update(data_storage_labels)

    resnet_training_cpu_function_requests = (
        KubernetesResourceConfiguration.create_from_str(cpu="1000m", memory="1Gi")
    )
    resnet_training_cpu_function = FunctionContainer(
        resnet_training_cpu_function_image,
        resource_config=resnet_training_cpu_function_requests,
        labels={"watchdog": "http", "workers": "4", "cluster": "2"},
    )

    resnet_training_cpu_function.labels.update(data_storage_labels)

    deployment = FunctionDeployment(
        resnet_training_function,
        [resnet_training_gpu_function, resnet_training_cpu_function],
        ScalingConfiguration() if scaling_config is None else scaling_config,
        ranking,
    )

    return deployment


def get_tf_gpu_deployment(
    ranking: DeploymentRanking, scaling_config: ScalingConfiguration = None
):
    # Design Time
    tf_gpu_function_image = FunctionImage(image=images.tf_gpu_manifest)
    tf_gpu_function = Function(
        name=images.tf_gpu_function, fn_images=[tf_gpu_function_image]
    )

    # Run time
    tf_gpu_function_requests = KubernetesResourceConfiguration.create_from_str(
        cpu="1000m", memory="300Mi"
    )
    tf_gpu_function_container = FunctionContainer(
        tf_gpu_function_image,
        resource_config=tf_gpu_function_requests,
        labels={
            "watchdog": "http",
            "workers": "4",
            "cluster": "3",
            "device.edgerun.io/accelerator": "GPU",
            "device.edgerun.io/vram": "2000",
        },
    )

    deployment = FunctionDeployment(
        tf_gpu_function,
        [tf_gpu_function_container],
        ScalingConfiguration() if scaling_config is None else scaling_config,
        ranking,
    )

    return deployment


def get_pi_deployment(
    ranking: DeploymentRanking, scaling_config: ScalingConfiguration = None
) -> FunctionDeployment:
    # Design Time
    pi_function_image = FunctionImage(image=images.pi_manifest)
    pi_function = Function(name=images.pi_function, fn_images=[pi_function_image])

    # Run time
    pi_function_requests = KubernetesResourceConfiguration.create_from_str(
        cpu="1000m", memory="100Mi"
    )

    pi_function_container = FunctionContainer(
        pi_function_image,
        resource_config=pi_function_requests,
        labels={"watchdog": "http", "workers": "4", "cluster": "1"},
    )

    deployment = FunctionDeployment(
        pi_function,
        [pi_function_container],
        ScalingConfiguration() if scaling_config is None else scaling_config,
        ranking,
    )

    return deployment


def get_fio_deployment(
    ranking: DeploymentRanking, scaling_config: ScalingConfiguration = None
) -> FunctionDeployment:
    # Design Time
    fio_function_image = FunctionImage(image=images.fio_manifest)
    fio_function = Function(name=images.fio_function, fn_images=[fio_function_image])

    # Run time
    fio_function_requests = KubernetesResourceConfiguration.create_from_str(
        cpu="1000m", memory="200Mi"
    )

    fio_function_container = FunctionContainer(
        fio_function_image,
        resource_config=fio_function_requests,
        labels={"watchdog": "http", "workers": "4", "cluster": "1"},
    )

    deployment = FunctionDeployment(
        fio_function,
        [fio_function_container],
        ScalingConfiguration() if scaling_config is None else scaling_config,
        ranking,
    )

    return deployment


def get_resnet_preprocessing_deployment(
    ranking: DeploymentRanking, scaling_config: ScalingConfiguration = None
):
    # Design time
    resnet_preprocessing_function_image = FunctionImage(
        image=images.resnet50_preprocessing_manifest
    )
    resnet_preprocessing_function = Function(
        name=images.resnet50_preprocessing_function,
        fn_images=[resnet_preprocessing_function_image],
    )

    # Run time
    data = storage.resnet_pre_bucket_item.name

    data_storage_labels = {
        "data.skippy.io/receives-from-storage": "14M",
        "data.skippy.io/sends-to-storage": "14M",
        "data.skippy.io/receives-from-storage/path": f"{storage.resnet_pre_bucket}/{data}",
        "data.skippy.io/sends-to-storage/path": f"{storage.resnet_pre_bucket}/preprocessed",
    }

    resnet_preprocessing_function_requests = (
        KubernetesResourceConfiguration.create_from_str(cpu="1000m", memory="100Mi")
    )

    resnet_preprocessing_function_container = FunctionContainer(
        fn_image=resnet_preprocessing_function_image,
        resource_config=resnet_preprocessing_function_requests,
        labels={"watchdog": "http", "workers": "4", "cluster": "1"},
    )

    resnet_preprocessing_function.labels.update(data_storage_labels)

    deployment = FunctionDeployment(
        resnet_preprocessing_function,
        [resnet_preprocessing_function_container],
        ScalingConfiguration() if scaling_config is None else scaling_config,
        ranking,
    )

    return deployment

def get_video_analytics_deployment(
    ranking: DeploymentRanking, scaling_config: ScalingConfiguration = None
) -> FunctionDeployment:
    # Design time
    video_analytics_function_image = FunctionImage(
        image=images.video_analytics_manifest
    )
    video_analytics_function = Function(
        name=images.video_analytics_function,
        fn_images=[video_analytics_function_image],
    )

    # Run time
    video_analytics_function_requests = KubernetesResourceConfiguration.create_from_str(
        cpu="1000m", memory="300Mi"
    )

    video_analytics_function_container = FunctionContainer(
        video_analytics_function_image,
        resource_config=video_analytics_function_requests,
        labels={"watchdog": "http", "workers": "2", "cluster": "video"},
    )

    deployment = FunctionDeployment(
        video_analytics_function,
        [video_analytics_function_container],
        ScalingConfiguration() if scaling_config is None else scaling_config,
        ranking,
    )

    return deployment


def get_iot_data_processor_deployment(
    ranking: DeploymentRanking, scaling_config: ScalingConfiguration = None
) -> FunctionDeployment:
    # Design time
    iot_data_processor_function_image = FunctionImage(
        image=images.iot_data_processor_manifest
    )
    iot_data_processor_function = Function(
        name=images.iot_data_processor_function,
        fn_images=[iot_data_processor_function_image],
    )

    # Run time
    iot_data_processor_function_requests = KubernetesResourceConfiguration.create_from_str(
        cpu="500m", memory="50Mi"
    )

    iot_data_processor_function_container = FunctionContainer(
        iot_data_processor_function_image,
        resource_config=iot_data_processor_function_requests,
        labels={"watchdog": "http", "workers": "4", "cluster": "iot"},
    )

    deployment = FunctionDeployment(
        iot_data_processor_function,
        [iot_data_processor_function_container],
        ScalingConfiguration() if scaling_config is None else scaling_config,
        ranking,
    )

    return deployment


def get_alert_service_deployment(
    ranking: DeploymentRanking, scaling_config: ScalingConfiguration = None
) -> FunctionDeployment:
    # Design time
    alert_service_function_image = FunctionImage(
        image=images.alert_service_manifest
    )
    alert_service_function = Function(
        name=images.alert_service_function,
        fn_images=[alert_service_function_image],
    )

    # Run time
    alert_service_function_requests = KubernetesResourceConfiguration.create_from_str(
        cpu="300m", memory="30Mi"
    )

    alert_service_function_container = FunctionContainer(
        alert_service_function_image,
        resource_config=alert_service_function_requests,
        labels={"watchdog": "http", "workers": "1", "cluster": "alert"},
    )

    deployment = FunctionDeployment(
        alert_service_function,
        [alert_service_function_container],
        ScalingConfiguration() if scaling_config is None else scaling_config,
        ranking,
    )

    return deployment


def get_data_aggregator_deployment(
    ranking: DeploymentRanking, scaling_config: ScalingConfiguration = None
) -> FunctionDeployment:
    # Design time
    data_aggregator_function_image = FunctionImage(
        image=images.data_aggregator_manifest
    )
    data_aggregator_function = Function(
        name=images.data_aggregator_function,
        fn_images=[data_aggregator_function_image],
    )

    # Run time
    data_aggregator_function_requests = KubernetesResourceConfiguration.create_from_str(
        cpu="1000m", memory="400Mi"
    )

    data_aggregator_function_container = FunctionContainer(
        data_aggregator_function_image,
        resource_config=data_aggregator_function_requests,
        labels={"watchdog": "http", "workers": "3", "cluster": "analytics"},
    )

    deployment = FunctionDeployment(
        data_aggregator_function,
        [data_aggregator_function_container],
        ScalingConfiguration() if scaling_config is None else scaling_config,
        ranking,
    )

    return deployment


def create_all_deployments(
    fet_oracle: FetOracle,
    resource_oracle: ResourceOracle,
    deployment_rankings: DeploymentSettings = None,
) -> Dict[str, FunctionDeployment]:
    if deployment_rankings is None:
        deployment_rankings = DeploymentSettings()
    return {
        images.resnet50_inference_function: get_resnet50_inference_deployment(
            deployment_rankings.resnet_inference_ranking
        ),
        images.resnet50_training_function: get_resnet_training_deployment(
            deployment_rankings.resnet_training_ranking
        ),
        images.mobilenet_inference_function: get_mobilenet_inference_deployment(
            deployment_rankings.mobilenet_inference_ranking
        ),
        # images.fio_function: get_fio_deployment(fet_oracle, resource_oracle, deployment_rankings.fio_ranking),
        # images.pi_function: get_pi_deployment(fet_oracle, resource_oracle, deployment_rankings.pi_ranking),
        # images.tf_gpu_function: get_tf_gpu_deployment(fet_oracle, resource_oracle, deployment_rankings.tf_gpu_ranking),
        images.speech_inference_function: get_speech_inference_deployment(
            deployment_rankings.speech_inference_ranking
        ),
        images.resnet50_preprocessing_function: get_resnet_preprocessing_deployment(
            deployment_rankings.resnet_preprocessing_ranking
        ),
        # ADD NEW SMART CITY FUNCTIONS HERE:
        images.video_analytics_function: get_video_analytics_deployment(
            deployment_rankings.video_analytics_ranking
        ),
        images.iot_data_processor_function: get_iot_data_processor_deployment(
            deployment_rankings.iot_data_processor_ranking
        ),
        images.alert_service_function: get_alert_service_deployment(
            deployment_rankings.alert_service_ranking
        ),
        images.data_aggregator_function: get_data_aggregator_deployment(
            deployment_rankings.data_aggregator_ranking
        ),
    }