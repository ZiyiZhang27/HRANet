log_level = 'INFO'
load_from = None
resume_from = None
dist_params = dict(backend='nccl')
workflow = [('train', 1)]
checkpoint_config = dict(interval=5)
evaluation = dict(interval=10, metric='mAP', save_best='AP')
find_unused_parameters = False

optimizer = dict(
    type='AdamW',
    lr=4e-3,
    betas=(0.9, 0.999),
    weight_decay=0.01,
    paramwise_cfg=dict(custom_keys={'relative_position_bias_table': dict(decay_mult=0.)})
)
optimizer_config = dict(grad_clip=None)

# learning policy
lr_config = dict(
    policy='CosineAnnealing',
    warmup='linear',
    warmup_iters=500,
    warmup_ratio=0.001,
    min_lr_ratio=0.01
)
total_epochs = 300

log_config = dict(
    interval=50,
    hooks=[
        dict(type='TextLoggerHook'),
        # dict(type='TensorboardLoggerHook')
    ]
)

channel_cfg = dict(
    num_output_channels=14,
    dataset_joints=14,
    dataset_channel=[
        [0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13],
    ],
    inference_channel=[0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13]
)

# model settings
model = dict(
    type='TopDown',
    backbone=dict(
        type='HRNeXt',
        in_channels=3,
        norm_cfg=dict(type='SyncBN'),
        with_cp=True,
        extra=dict(
            drop_path_rate=0.1,
            stage1=dict(
                num_modules=1,
                num_branches=1,
                block='HRNEXT_BLOCK',
                num_blocks=(2,),
                num_channels=(64,),
                num_mlp_ratios=(4,),
                num_kernels=(4,)
            ),
            stage2=dict(
                num_modules=2,
                num_branches=2,
                block='HRNEXT_BLOCK',
                num_blocks=(2, 2),
                num_channels=(32, 64),
                num_mlp_ratios=(4, 4),
                num_kernels=(4, 2)
            ),
            stage3=dict(
                num_modules=4,
                num_branches=3,
                block='HRNEXT_BLOCK',
                num_blocks=(2, 2, 2),
                num_channels=(32, 64, 128),
                num_mlp_ratios=(4, 4, 4),
                num_kernels=(4, 2, 1)
            ),
            stage4=dict(
                num_modules=2,
                num_branches=4,
                block='HRNEXT_BLOCK',
                num_blocks=(2, 2, 2, 2),
                num_channels=(32, 64, 128, 256),
                num_mlp_ratios=(4, 4, 4, 4),
                num_kernels=(4, 2, 1, 1)
            )
        )
    ),
    keypoint_head=dict(
        type='TopdownHeatmapSimpleHead',
        in_channels=32,
        out_channels=channel_cfg['num_output_channels'],
        num_deconv_layers=0,
        extra=dict(final_conv_kernel=1, ),
        loss_keypoint=dict(type='JointsMSELoss', use_target_weight=True)
    ),
    train_cfg=dict(),
    test_cfg=dict(
        flip_test=True,
        post_process='default',
        shift_heatmap=True,
        modulate_kernel=11,
        use_udp=False
    )
)

data_cfg = dict(
    image_size=[288, 384],
    heatmap_size=[72, 96],
    num_output_channels=channel_cfg['num_output_channels'],
    num_joints=channel_cfg['dataset_joints'],
    dataset_channel=channel_cfg['dataset_channel'],
    inference_channel=channel_cfg['inference_channel'],
    crowd_matching=False,
    soft_nms=False,
    nms_thr=1.0,
    oks_thr=0.9,
    vis_thr=0.2,
    use_gt_bbox=False,
    det_bbox_thr=0.0,
    bbox_file='data/crowdpose/annotations/det_for_crowd_test_0.1_0.5.json'
)

train_pipeline = [
    dict(type='LoadImageFromFile'),
    dict(type='TopDownRandomFlip', flip_prob=0.5),
    dict(
        type='TopDownHalfBodyTransform',
        num_joints_half_body=6,
        prob_half_body=0.3
    ),
    dict(
        type='TopDownGetRandomScaleRotation',
        rot_factor=40,
        scale_factor=0.5
    ),
    dict(type='TopDownAffine', use_udp=False),
    dict(type='ToTensor'),
    dict(
        type='NormalizeTensor',
        mean=[0.485, 0.456, 0.406],
        std=[0.229, 0.224, 0.225]
    ),
    dict(type='TopDownGenerateTarget', sigma=3),
    dict(
        type='Collect',
        keys=['img', 'target', 'target_weight'],
        meta_keys=[
            'image_file', 'joints_3d', 'joints_3d_visible', 'center', 'scale',
            'rotation', 'bbox_score', 'flip_pairs'
        ]
    )
]

val_pipeline = [
    dict(type='LoadImageFromFile'),
    dict(type='TopDownAffine', use_udp=False),
    dict(type='ToTensor'),
    dict(
        type='NormalizeTensor',
        mean=[0.485, 0.456, 0.406],
        std=[0.229, 0.224, 0.225]
    ),
    dict(
        type='Collect',
        keys=['img'],
        meta_keys=[
            'image_file', 'center', 'scale', 'rotation', 'bbox_score',
            'flip_pairs'
        ]
    )
]

test_pipeline = val_pipeline

data = dict(
    samples_per_gpu=64,
    workers_per_gpu=6,
    val_dataloader=dict(samples_per_gpu=256),
    test_dataloader=dict(samples_per_gpu=256),
    pin_memory=True,
    train=dict(
        type='TopDownCrowdPoseDataset',
        ann_file='data/crowdpose/annotations/mmpose_crowdpose_trainval.json',
        img_prefix='data/crowdpose/images/',
        data_cfg=data_cfg,
        pipeline=train_pipeline
    ),
    val=dict(
        type='TopDownCrowdPoseDataset',
        ann_file='data/crowdpose/annotations/mmpose_crowdpose_test.json',
        img_prefix='data/crowdpose/images/',
        data_cfg=data_cfg,
        pipeline=val_pipeline
    ),
    test=dict(
        type='TopDownCrowdPoseDataset',
        ann_file='data/crowdpose/annotations/mmpose_crowdpose_test.json',
        img_prefix='data/crowdpose/images/',
        data_cfg=data_cfg,
        pipeline=test_pipeline
    )
)
