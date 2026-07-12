(function () {
  const sections = [
    {
        "id":  "common-color",
        "title":  "Color Errors",
        "cases":  [
                      {
                          "title":  "Case 1: area_2.png",
                          "level":  "Level 1",
                          "levelCode":  "task1",
                          "model":  "gpt_5.2_direct",
                          "kind":  "error",
                          "groundTruth":  "data1/data/level1_direct/area_2.png",
                          "output":  "data1/data/gpt_5.2_direct/area_2.png",
                          "analysis":  "The color of the bottom subplot in the model output on the right does not match the GT Figure; the model failed to understand the color-coded regions in the area chart."
                      },
                      {
                          "title":  "Case 2: area_5.png",
                          "level":  "Level 1",
                          "levelCode":  "task1",
                          "model":  "gpt_5.2_direct",
                          "kind":  "error",
                          "groundTruth":  "data1/data/level1_direct/area_5.png",
                          "output":  "data1/data/gpt_5.2_direct/area_5.png",
                          "analysis":  "A clear deviation in color representation is evident between the generated result (right) and the ground-truth (GT) figure across both the upper and lower subplots. This discrepancy indicates insufficient sensitivity to color details, leading to inaccurate reproduction of the original color encoding."
                      },
                      {
                          "title":  "Case 3: heatmap_40.png",
                          "level":  "Level 1",
                          "levelCode":  "task1",
                          "model":  "gpt_5.2_direct",
                          "kind":  "error",
                          "groundTruth":  "data1/data/level1_direct/heatmap_40.png",
                          "output":  "data1/data/gpt_5.2_direct/heatmap_40.png",
                          "analysis":  "Significant discrepancies in color transitions are observed between the model-generated output (right) and the ground-truth (GT) figure, indicating limitations in the model\u0027s ability to accurately perceive and reproduce subtle variations in color."
                      },
                      {
                          "title":  "Case 4: bar_7.png",
                          "level":  "Level 1",
                          "levelCode":  "task1",
                          "model":  "seed_1.6_direct",
                          "kind":  "error",
                          "groundTruth":  "data1/data/level1_direct/bar_7.png",
                          "output":  "data1/data/seed_1.6_direct/bar_7.png",
                          "analysis":  "The color filling in the model output on the right is completely opposite to that of the GT Figure, indicating the model\u0027s inability to accurately recognize colors. Additionally, there are issues with the recognition of the legend."
                      },
                      {
                          "title":  "Case 5: area_4_v1.png",
                          "level":  "Level 2",
                          "levelCode":  "task2",
                          "model":  "gemini_3_pro_level2",
                          "kind":  "error",
                          "groundTruth":  "data1/data/level2/area_4_v1.png",
                          "output":  "data1/data/gemini_3_pro_level2/area_4_v1.png",
                          "analysis":  "The color filling in the model output on the right is inconsistent with the GT Figure and lacks visual appeal; the transparency of the filled colors in the area regions has not been appropriately adjusted."
                      },
                      {
                          "title":  "Case 6: combination_18_v1.png",
                          "level":  "Level 2",
                          "levelCode":  "task2",
                          "model":  "gpt_5.2_level2",
                          "kind":  "error",
                          "groundTruth":  "data1/data/level2/combination_18_v1.png",
                          "output":  "data1/data/gpt_5.2_level2/combination_18_v1.png",
                          "analysis":  "The legend colors in the model output on the right do not match those in the GT Figure, and there is a noticeable color discrepancy at X=18. This indicates that the model lacks fine-grained image perception capabilities in complex charts."
                      },
                      {
                          "title":  "Case 7: bar_30_v2.png",
                          "level":  "Level 2",
                          "levelCode":  "task2",
                          "model":  "seed_1.6_level2",
                          "kind":  "error",
                          "groundTruth":  "data1/data/level2/bar_30_v2.png",
                          "output":  "data1/data/seed_1.6_level2/bar_30_v2.png",
                          "analysis":  "The legend colors in the model output on the right do not match those in the GT Figure. Most notably, the blue line in the bottom subplot, which should be above y=0, is incorrectly interpreted as being below it. Additionally, the amount of data in the upper subplot is also incorrect."
                      },
                      {
                          "title":  "Case 8: table1_8_generate.png",
                          "level":  "Level 3",
                          "levelCode":  "task3",
                          "model":  "seed_1.6_level3",
                          "kind":  "error",
                          "groundTruth":  "data1/data/level3/table1_8_generate.png",
                          "output":  "data1/data/seed_1.6_level3/table1_8_generate.png",
                          "analysis":  "Due to a bottleneck in visual perception, the model failed to identify and extract the unique color mapping for each category, resulting in a generated chart that mistakenly uses a monochromatic scheme and loses key visual discriminative features and and suffering from severe text overlapping on the X-axis."
                      },
                      {
                          "title":  "Case 9: table32_3_generate.png",
                          "level":  "Level 3",
                          "levelCode":  "task3",
                          "model":  "seed_1.6_level3",
                          "kind":  "error",
                          "groundTruth":  "data1/data/level3/table32_3_generate.png",
                          "output":  "data1/data/seed_1.6_level3/table32_3_generate.png",
                          "analysis":  "Although the model identified the color sequence in the legend area, this perception failed to transfer to the plot objects within the coordinate system, reflecting a logical inconsistency between local feature recognition and global mapping."
                      }
                  ]
    },
    {
        "id":  "common-component-position",
        "title":  "Component Position Errors",
        "cases":  [
                      {
                          "title":  "Case 1: bar_24.png",
                          "level":  "Level 1",
                          "levelCode":  "task1",
                          "model":  "gpt_5.2_direct",
                          "kind":  "error",
                          "groundTruth":  "data1/data/level1_direct/bar_24.png",
                          "output":  "data1/data/gpt_5.2_direct/bar_24.png",
                          "analysis":  "The text positioning in the model output on the right does not match that of the GT Figure, resulting in noticeable visual overlap and affecting the aesthetic quality."
                      },
                      {
                          "title":  "Case 2: bar_86.png",
                          "level":  "Level 1",
                          "levelCode":  "task1",
                          "model":  "qwen3_direct_30B",
                          "kind":  "error",
                          "groundTruth":  "data1/data/level1_direct/bar_86.png",
                          "output":  "data1/data/qwen3_direct_30B/bar_86.png",
                          "analysis":  "The legend position in the model output on the right does not match that of the GT Figure, causing visual overlap with the right axis and affecting the aesthetic quality. Additionally, the arrangement order of the bars in the bar chart is also incorrect."
                      },
                      {
                          "title":  "Case 3: bar_14.png",
                          "level":  "Level 1",
                          "levelCode":  "task1",
                          "model":  "seed_1.6_direct",
                          "kind":  "error",
                          "groundTruth":  "data1/data/level1_direct/bar_14.png",
                          "output":  "data1/data/seed_1.6_direct/bar_14.png",
                          "analysis":  "The legend position in the model output on the right does not match that of the GT Figure, and the placement of the numerical values is also completely different."
                      },
                      {
                          "title":  "Case 4: bar_37.png",
                          "level":  "Level 1",
                          "levelCode":  "task1",
                          "model":  "qwen3_direct_30B",
                          "kind":  "error",
                          "groundTruth":  "data1/data/level1_direct/bar_37.png",
                          "output":  "data1/data/qwen3_direct_30B/bar_37.png",
                          "analysis":  "The legend position in the model output on the right does not match that of the GT Figure, severely obscuring the data portion of the bar chart and causing significant visibility issues."
                      },
                      {
                          "title":  "Case 5: errorpoint_7_v3.png",
                          "level":  "Level 2",
                          "levelCode":  "task2",
                          "model":  "seed_1.6_level2",
                          "kind":  "error",
                          "groundTruth":  "data1/data/level2/errorpoint_7_v3.png",
                          "output":  "data1/data/seed_1.6_level2/errorpoint_7_v3.png",
                          "analysis":  "The subplot position in the model output on the right does not match that of the GT Figure, severely obscuring the data portion of the error points and causing significant visibility issues."
                      },
                      {
                          "title":  "Case 6: errorpoint_8_v2.png",
                          "level":  "Level 2",
                          "levelCode":  "task2",
                          "model":  "seed_1.6_level2",
                          "kind":  "error",
                          "groundTruth":  "data1/data/level2/errorpoint_8_v2.png",
                          "output":  "data1/data/seed_1.6_level2/errorpoint_8_v2.png",
                          "analysis":  "The legend position in the model output on the right does not match that of the GT Figure, severely obscuring the chart title and making the letters in the title illegible."
                      },
                      {
                          "title":  "Case 7: quiver_4_v1.png",
                          "level":  "Level 2",
                          "levelCode":  "task2",
                          "model":  "seed_1.6_level2",
                          "kind":  "error",
                          "groundTruth":  "data1/data/level2/quiver_4_v1.png",
                          "output":  "data1/data/seed_1.6_level2/quiver_4_v1.png",
                          "analysis":  "The color bar position in the model output on the right does not match that of the GT Figure, severely obscuring the internal data of the chart and also resulting in an extremely unaesthetic appearance."
                      },
                      {
                          "title":  "Case 8: table31_1_generate.png",
                          "level":  "Level 3",
                          "levelCode":  "task3",
                          "model":  "seed_1.6_level3",
                          "kind":  "error",
                          "groundTruth":  "data1/data/level3/table31_1_generate.png",
                          "output":  "data1/data/seed_1.6_level3/table31_1_generate.png",
                          "analysis":  "The model failed to accurately extract the absolute spatial coordinates of the legend, leading to positional displacement and visual overlapping with the title, reflecting a failure in spatial perception for complex layouts."
                      },
                      {
                          "title":  "Case 9: table33_1_generate.png",
                          "level":  "Level 3",
                          "levelCode":  "task3",
                          "model":  "seed_1.6_level3",
                          "kind":  "error",
                          "groundTruth":  "data1/data/level3/table33_1_generate.png",
                          "output":  "data1/data/seed_1.6_level3/table33_1_generate.png",
                          "analysis":  "The model exhibits a clear visual perception bottleneck in spatial reasoning, failing to recognize the physical boundaries between the legend, title, and chart body. This leads to severe visual overlapping and positional misalignment, as the model overlooks the layout constraints required to prevent component occlusion."
                      }
                  ]
    },
    {
        "id":  "common-data-encoding",
        "title":  "Data Encoding Errors",
        "cases":  [
                      {
                          "title":  "Case 1: density_2.png",
                          "level":  "Level 1",
                          "levelCode":  "task1",
                          "model":  "gpt_5.2_direct",
                          "kind":  "error",
                          "groundTruth":  "data1/data/level1_direct/density_2.png",
                          "output":  "data1/data/gpt_5.2_direct/density_2.png",
                          "analysis":  "The data distribution in the model output on the right is inconsistent with that of the GT Figure, indicating insufficient data accuracy and a deficiency in the model\u0027s ability to recognize and analyze the original chart\u0027s data."
                      },
                      {
                          "title":  "Case 2: combination_66.png",
                          "level":  "Level 1",
                          "levelCode":  "task1",
                          "model":  "qwen3_direct_30B",
                          "kind":  "error",
                          "groundTruth":  "data1/data/level1_direct/combination_66.png",
                          "output":  "data1/data/qwen3_direct_30B/combination_66.png",
                          "analysis":  "The generated output (right) exhibits inconsistencies in data distribution compared with the ground-truth (GT) figure, reflecting deficiencies in data representation accuracy and limitations in the model\u0027s ability to correctly analyze the source chart."
                      },
                      {
                          "title":  "Case 3: radar_1.png",
                          "level":  "Level 1",
                          "levelCode":  "task1",
                          "model":  "seed_1.6_direct",
                          "kind":  "error",
                          "groundTruth":  "data1/data/level1_direct/radar_1.png",
                          "output":  "data1/data/seed_1.6_direct/radar_1.png",
                          "analysis":  "The data distribution in the model output on the right is inconsistent with that of the GT Figure, indicating insufficient data accuracy and a deficiency in the model\u0027s ability to recognize and analyze the original chart\u0027s data."
                      },
                      {
                          "title":  "Case 4: combination_3_v3.png",
                          "level":  "Level 2",
                          "levelCode":  "task2",
                          "model":  "seed_1.6_level2",
                          "kind":  "error",
                          "groundTruth":  "data1/data/level2/combination_3_v3.png",
                          "output":  "data1/data/seed_1.6_level2/combination_3_v3.png",
                          "analysis":  "The data distribution in the model output on the right is inconsistent with that of the GT Figure, indicating insufficient data accuracy and a deficiency in the model\u0027s ability to recognize and analyze the original chart\u0027s data."
                      },
                      {
                          "title":  "Case 5: bar_19_v1.png",
                          "level":  "Level 2",
                          "levelCode":  "task2",
                          "model":  "seed_1.6_level2",
                          "kind":  "error",
                          "groundTruth":  "data1/data/level2/bar_19_v1.png",
                          "output":  "data1/data/seed_1.6_level2/bar_19_v1.png",
                          "analysis":  "The generated output (right) exhibits inconsistencies in data distribution compared with the ground-truth (GT) figure, including the omission of an entire data series, reflecting deficiencies in data representation accuracy and limitations in the model\u0027s ability to correctly analyze the source chart."
                      },
                      {
                          "title":  "Case 6: pie_5_v3.png",
                          "level":  "Level 2",
                          "levelCode":  "task2",
                          "model":  "seed_1.6_level2",
                          "kind":  "error",
                          "groundTruth":  "data1/data/level2/pie_5_v3.png",
                          "output":  "data1/data/seed_1.6_level2/pie_5_v3.png",
                          "analysis":  "The data distribution in the model output on the right is inconsistent with that of the GT Figure, indicating insufficient data accuracy and a deficiency in the model\u0027s ability to recognize and analyze the original chart\u0027s data."
                      },
                      {
                          "title":  "Case 7: table4_4_generate.png",
                          "level":  "Level 3",
                          "levelCode":  "task3",
                          "model":  "seed_1.6_level3",
                          "kind":  "error",
                          "groundTruth":  "data1/data/level3/table4_4_generate.png",
                          "output":  "data1/data/seed_1.6_level3/table4_4_generate.png",
                          "analysis":  "In the generated heatmap, the model only reproduced the data for the \"Total\" indicator, completely omitting all other component indicators (e.g., S1, S2, C3, E3, etc.), which reflects a critical failure in data extraction and comprehensive information reproduction capabilities."
                      },
                      {
                          "title":  "Case 8: table3_1_generate.png",
                          "level":  "Level 3",
                          "levelCode":  "task3",
                          "model":  "claude_level3",
                          "kind":  "error",
                          "groundTruth":  "data1/data/level3/table3_1_generate.png",
                          "output":  "data1/data/claude_level3/table3_1_generate.png",
                          "analysis":  "The model made critical errors in data extraction, failing to accurately reproduce the histogram bar heights, KDE curve shape, and X-axis range from the ground truth, resulting in a fundamentally incorrect data distribution."
                      }
                  ]
    },
    {
        "id":  "common-axis-scale",
        "title":  "Axis Scale Errors",
        "cases":  [
                      {
                          "title":  "Case 1: combination_61.png",
                          "level":  "Level 1",
                          "levelCode":  "task1",
                          "model":  "qwen3_direct_30B",
                          "kind":  "error",
                          "groundTruth":  "data1/data/level1_direct/combination_61.png",
                          "output":  "data1/data/qwen3_direct_30B/combination_61.png",
                          "analysis":  "The y-axis range in the model output on the right is problematic, causing part of the data to be invisible. This indicates an insufficient match between the axis range and the data. Additionally, errors occurred in data recognition and analysis."
                      },
                      {
                          "title":  "Case 2: contour_2.png",
                          "level":  "Level 1",
                          "levelCode":  "task1",
                          "model":  "seed_1.6_direct",
                          "kind":  "error",
                          "groundTruth":  "data1/data/level1_direct/contour_2.png",
                          "output":  "data1/data/seed_1.6_direct/contour_2.png",
                          "analysis":  "The generated output (right) adopts an unsuitable y-axis range, resulting in incomplete data visualization. Such inconsistency suggests improper scaling relative to the dataset and highlights limitations in the model\u0027s data extraction and analytical capabilities."
                      },
                      {
                          "title":  "Case 3: area_11.png",
                          "level":  "Level 1",
                          "levelCode":  "task1",
                          "model":  "claude_direct",
                          "kind":  "error",
                          "groundTruth":  "data1/data/level1_direct/area_11.png",
                          "output":  "data1/data/claude_direct/area_11.png",
                          "analysis":  "The y-axis range in the model output on the right is problematic, causing part of the data to be invisible. This indicates an insufficient match between the axis range and the data. Additionally, errors occurred in data recognition and analysis."
                      },
                      {
                          "title":  "Case 4: area_1_v2.png",
                          "level":  "Level 2",
                          "levelCode":  "task2",
                          "model":  "gpt_5.2_level2",
                          "kind":  "error",
                          "groundTruth":  "data1/data/level2/area_1_v2.png",
                          "output":  "data1/data/gpt_5.2_level2/area_1_v2.png",
                          "analysis":  "In the generated chart, the Y-axis range of the left subplot is incorrectly compressed to 0.53-0.76, and the legend is misplaced over the data area, both of which severely distort the data representation and visual clarity compared to the ground truth."
                      },
                      {
                          "title":  "Case 5: bar_1_v3.png",
                          "level":  "Level 2",
                          "levelCode":  "task2",
                          "model":  "gpt_5.2_level2",
                          "kind":  "error",
                          "groundTruth":  "data1/data/level2/bar_1_v3.png",
                          "output":  "data1/data/gpt_5.2_level2/bar_1_v3.png",
                          "analysis":  "In the model-generated chart, the y-axis range is incorrectly set to 0-0.5, which is narrower than the 0-1 range in the ground truth, resulting in the upper portion of the stacked area chart being truncated. Additionally, the leftmost segment of the chart is missing. These issues indicate deficiencies in the model\u0027s data extraction capability and its ability to accurately infer the underlying numerical scale."
                      }
                  ]
    },
    {
        "id":  "common-type",
        "title":  "Type Errors",
        "cases":  [
                      {
                          "title":  "Case 1: combination_34.png",
                          "level":  "Level 1",
                          "levelCode":  "task1",
                          "model":  "qwen2.5_direct_72B",
                          "kind":  "error",
                          "groundTruth":  "data1/data/level1_direct/combination_34.png",
                          "output":  "data1/data/qwen2.5_direct_72B/combination_34.png",
                          "analysis":  "The chart type in the model output on the right is inconsistent with that of the GT Figure; the scatter plot has been misidentified as a contour plot."
                      },
                      {
                          "title":  "Case 2: bar_42.png",
                          "level":  "Level 1",
                          "levelCode":  "task1",
                          "model":  "claude_direct",
                          "kind":  "error",
                          "groundTruth":  "data1/data/level1_direct/bar_42.png",
                          "output":  "data1/data/claude_direct/bar_42.png",
                          "analysis":  "The chart type in the model output on the right is inconsistent with the GT Figure; the regular bar chart has been misidentified as a stacked bar chart, which deviates significantly from the original."
                      },
                      {
                          "title":  "Case 3: combination_38.png",
                          "level":  "Level 1",
                          "levelCode":  "task1",
                          "model":  "qwen2.5_direct_72B",
                          "kind":  "error",
                          "groundTruth":  "data1/data/level1_direct/combination_38.png",
                          "output":  "data1/data/qwen2.5_direct_72B/combination_38.png",
                          "analysis":  "The chart type in the model output on the right is inconsistent with that of the GT Figure; the right subplot differs significantly from the right subplot of the GT Figure."
                      },
                      {
                          "title":  "Case 4: bar_10_v2.png",
                          "level":  "Level 2",
                          "levelCode":  "task2",
                          "model":  "qwen2.5_level2_72B",
                          "kind":  "error",
                          "groundTruth":  "data1/data/level2/bar_10_v2.png",
                          "output":  "data1/data/qwen2.5_level2_72B/bar_10_v2.png",
                          "analysis":  "The chart type in the model output on the right is inconsistent with the GT Figure; the bar chart on the right differs significantly from the stacked bar chart in the GT Figure."
                      },
                      {
                          "title":  "Case 5: line_11_v5.png",
                          "level":  "Level 2",
                          "levelCode":  "task2",
                          "model":  "qwen2.5_level2_72B",
                          "kind":  "error",
                          "groundTruth":  "data1/data/level2/line_11_v5.png",
                          "output":  "data1/data/qwen2.5_level2_72B/line_11_v5.png",
                          "analysis":  "The chart type in the model output on the right is inconsistent with that of the GT Figure; the right subplot differs significantly from the corresponding subplot in the GT Figure. The orientation of the bars in the bar chart is inconsistent, and there are notable differences in the remaining parts as well."
                      },
                      {
                          "title":  "Case 6: bar_24_v5.png",
                          "level":  "Level 2",
                          "levelCode":  "task2",
                          "model":  "qwen2.5_level2_72B",
                          "kind":  "error",
                          "groundTruth":  "data1/data/level2/bar_24_v5.png",
                          "output":  "data1/data/qwen2.5_level2_72B/bar_24_v5.png",
                          "analysis":  "The chart type in the model output on the right does not match the GT Figure. The subplot in the upper-right corner differs from the corresponding subplot in the GT Figure, and there are also issues with grid line settings and text overlap."
                      },
                      {
                          "title":  "Case 7: table2_5_generate.png",
                          "level":  "Level 3",
                          "levelCode":  "task3",
                          "model":  "claude_level3",
                          "kind":  "error",
                          "groundTruth":  "data1/data/level3/table2_5_generate.png",
                          "output":  "data1/data/claude_level3/table2_5_generate.png",
                          "analysis":  "The chart type in the model output on the right differs from that of the GT Figure. The GT Figure is a violin chart, but the model generated a box chart."
                      },
                      {
                          "title":  "Case 8: table52_1_generate.png",
                          "level":  "Level 3",
                          "levelCode":  "task3",
                          "model":  "seed_1.6_level3",
                          "kind":  "error",
                          "groundTruth":  "data1/data/level3/table52_1_generate.png",
                          "output":  "data1/data/seed_1.6_level3/table52_1_generate.png",
                          "analysis":  "The chart type in the model output on the right differs from that of the GT Figure. The GT Figure is a circular bar chart, but the model generated a regular bar chart."
                      }
                  ]
    },
    {
        "id":  "common-grid",
        "title":  "Grid Errors",
        "cases":  [
                      {
                          "title":  "Case 1: line_22.png",
                          "level":  "Level 1",
                          "levelCode":  "task1",
                          "model":  "qwen3_direct_30B",
                          "kind":  "error",
                          "groundTruth":  "data1/data/level1_direct/line_22.png",
                          "output":  "data1/data/qwen3_direct_30B/line_22.png",
                          "analysis":  "The grid line style in the model-generated output (right) is inconsistent with that of the ground-truth (GT) figure, with dashed lines appearing on the right side where they are not present in the reference. This discrepancy indicates a deficiency in the model\u0027s ability to perceive and faithfully reproduce fine-grained visual details."
                      },
                      {
                          "title":  "Case 2: line_25.png",
                          "level":  "Level 1",
                          "levelCode":  "task1",
                          "model":  "seed_1.6_direct",
                          "kind":  "error",
                          "groundTruth":  "data1/data/level1_direct/line_25.png",
                          "output":  "data1/data/seed_1.6_direct/line_25.png",
                          "analysis":  "The grid line style in the model output on the right is inconsistent with that of the GT Figure, indicating a deficiency in the model\u0027s ability to perceive fine-grained visual details."
                      },
                      {
                          "title":  "Case 3: combination_8_v4.png",
                          "level":  "Level 2",
                          "levelCode":  "task2",
                          "model":  "seed_1.6_level2",
                          "kind":  "error",
                          "groundTruth":  "data1/data/level2/combination_8_v4.png",
                          "output":  "data1/data/seed_1.6_level2/combination_8_v4.png",
                          "analysis":  "The grid line style in the model output on the right is inconsistent with that of the GT Figure, indicating a deficiency in the model\u0027s ability to perceive fine-grained visual details."
                      },
                      {
                          "title":  "Case 4: combination_9_v3.png",
                          "level":  "Level 2",
                          "levelCode":  "task2",
                          "model":  "seed_1.6_level2",
                          "kind":  "error",
                          "groundTruth":  "data1/data/level2/combination_9_v3.png",
                          "output":  "data1/data/seed_1.6_level2/combination_9_v3.png",
                          "analysis":  "The grid line style in the model output on the right is inconsistent with that of the GT Figure, indicating a deficiency in the model\u0027s ability to perceive fine-grained visual details."
                      },
                      {
                          "title":  "Case 5: combination_39_v1.png",
                          "level":  "Level 2",
                          "levelCode":  "task2",
                          "model":  "qwen2.5_level2_72B",
                          "kind":  "error",
                          "groundTruth":  "data1/data/level2/combination_39_v1.png",
                          "output":  "data1/data/qwen2.5_level2_72B/combination_39_v1.png",
                          "analysis":  "The grid line style in the model output on the right is inconsistent with that of the GT Figure, indicating a deficiency in the model\u0027s ability to perceive fine-grained visual details."
                      },
                      {
                          "title":  "Case 6: table52_7_generate.png",
                          "level":  "Level 3",
                          "levelCode":  "task3",
                          "model":  "seed_1.6_level3",
                          "kind":  "error",
                          "groundTruth":  "data1/data/level3/table52_7_generate.png",
                          "output":  "data1/data/seed_1.6_level3/table52_7_generate.png",
                          "analysis":  "The grid line style in the model output on the right differs from that of the GT Figure; the vertical grid lines are missing."
                      },
                      {
                          "title":  "Case 7: table2_3_generate.png",
                          "level":  "Level 3",
                          "levelCode":  "task3",
                          "model":  "claude_level3",
                          "kind":  "error",
                          "groundTruth":  "data1/data/level3/table2_3_generate.png",
                          "output":  "data1/data/claude_level3/table2_3_generate.png",
                          "analysis":  "The grid line style in the model output on the right differs from that of the GT Figure. In the original figure, there are no horizontal grid lines. Additionally, there are issues with the data in the chart."
                      }
                  ]
    },
    {
        "id":  "common-text-occlusion",
        "title":  "Text Occlusion Errors",
        "cases":  [
                      {
                          "title":  "Case 1: bar_12_v1.png",
                          "level":  "Level 2",
                          "levelCode":  "task2",
                          "model":  "gpt_5.2_level2",
                          "kind":  "error",
                          "groundTruth":  "data1/data/level2/bar_12_v1.png",
                          "output":  "data1/data/gpt_5.2_level2/bar_12_v1.png",
                          "analysis":  "There is a serious text overlap issue in the model output on the right, with overlapping text between the upper and lower subplots, which severely affects the visual aesthetics."
                      },
                      {
                          "title":  "Case 2: bar_17_v5.png",
                          "level":  "Level 2",
                          "levelCode":  "task2",
                          "model":  "gpt_5.2_level2",
                          "kind":  "error",
                          "groundTruth":  "data1/data/level2/bar_17_v5.png",
                          "output":  "data1/data/gpt_5.2_level2/bar_17_v5.png",
                          "analysis":  "The legend and title in the model output on the right severely overlap, significantly impacting the visual aesthetics."
                      },
                      {
                          "title":  "Case 3: HR_9_v5.png",
                          "level":  "Level 2",
                          "levelCode":  "task2",
                          "model":  "seed_1.6_level2",
                          "kind":  "error",
                          "groundTruth":  "data1/data/level2/HR_9_v5.png",
                          "output":  "data1/data/seed_1.6_level2/HR_9_v5.png",
                          "analysis":  "There is severe overlap among the labels in the model output on the right, which greatly impacts the visual aesthetics. Additionally, there is a noticeable deficiency in the recognition of numerical values."
                      },
                      {
                          "title":  "Case 4: errorbar_8.png",
                          "level":  "Level 1",
                          "levelCode":  "task1",
                          "model":  "qwen2.5_direct_72B",
                          "kind":  "error",
                          "groundTruth":  "data1/data/level1_direct/errorbar_8.png",
                          "output":  "data1/data/qwen2.5_direct_72B/errorbar_8.png",
                          "analysis":  "The model\u0027s output chart exhibits repeated rendering and severe overlap of y-axis labels, indicating significant shortcomings in its spatial layout and text rendering capabilities."
                      },
                      {
                          "title":  "Case 5: bar_22.png",
                          "level":  "Level 1",
                          "levelCode":  "task1",
                          "model":  "qwen3_direct_30B",
                          "kind":  "error",
                          "groundTruth":  "data1/data/level1_direct/bar_22.png",
                          "output":  "data1/data/qwen3_direct_30B/bar_22.png",
                          "analysis":  "The model\u0027s generated chart suffers from severe text overlap, with dense, illegible labels on both the x-axis and legend, which is a direct result of the model\u0027s insufficient spatial layout and text rendering capabilities."
                      }
                  ]
    },
    {
        "id":  "common-visual-style",
        "title":  "Visual Style Errors",
        "cases":  [
                      {
                          "title":  "Case 1: bar_14_v3.png",
                          "level":  "Level 2",
                          "levelCode":  "task2",
                          "model":  "qwen2.5_level2_72B",
                          "kind":  "error",
                          "groundTruth":  "data1/data/level2/bar_14_v3.png",
                          "output":  "data1/data/qwen2.5_level2_72B/bar_14_v3.png",
                          "analysis":  "The transparency in the left plot of the model output on the right is inconsistent with that of the GT Figure. Additionally, the legend style differs - the GT Figure uses a dashed line, while the model output uses a solid line. Furthermore, the text bolding also deviates from the GT Figure."
                      },
                      {
                          "title":  "Case 2: bar_17_v1.png",
                          "level":  "Level 2",
                          "levelCode":  "task2",
                          "model":  "qwen2.5_level2_72B",
                          "kind":  "error",
                          "groundTruth":  "data1/data/level2/bar_17_v1.png",
                          "output":  "data1/data/qwen2.5_level2_72B/bar_17_v1.png",
                          "analysis":  "The colors in the left plot of the model output on the right are inconsistent with those in the GT Figure, and the legend positions also differ. In the GT Figure, the bar chart on the right uses different colors, whereas in the model output, it is white."
                      },
                      {
                          "title":  "Case 3: bar_17_v3.png",
                          "level":  "Level 2",
                          "levelCode":  "task2",
                          "model":  "qwen2.5_level2_72B",
                          "kind":  "error",
                          "groundTruth":  "data1/data/level2/bar_17_v3.png",
                          "output":  "data1/data/qwen2.5_level2_72B/bar_17_v3.png",
                          "analysis":  "The filling patterns of the bar chart in the left plot of the model output on the right are inconsistent with those in the GT Figure, and the legend styles also differ. Additionally, the chart in the lower-right corner exhibits a chart type recognition error."
                      },
                      {
                          "title":  "Case 4: bar_16.png",
                          "level":  "Level 1",
                          "levelCode":  "task1",
                          "model":  "qwen2.5_direct_72B",
                          "kind":  "error",
                          "groundTruth":  "data1/data/level1_direct/bar_16.png",
                          "output":  "data1/data/qwen2.5_direct_72B/bar_16.png",
                          "analysis":  "In the generated chart, the dashed grid lines that were present in the ground truth are completely missing, which directly reflects the model\u0027s failure to capture and reproduce fine-grained visual attributes."
                      },
                      {
                          "title":  "Case 5: bar_18.png",
                          "level":  "Level 1",
                          "levelCode":  "task1",
                          "model":  "qwen2.5_direct_72B",
                          "kind":  "error",
                          "groundTruth":  "data1/data/level1_direct/bar_18.png",
                          "output":  "data1/data/qwen2.5_direct_72B/bar_18.png",
                          "analysis":  "In the generated chart, the dashed grid lines present in the ground truth are completely missing, and the color gradients are not accurately replicated. This directly reflects the model\u0027s failure to capture and reproduce fine-grained visual attributes."
                      },
                      {
                          "title":  "Case 6: table3_5_generate.png",
                          "level":  "Level 3",
                          "levelCode":  "task3",
                          "model":  "seed_1.6_level3",
                          "kind":  "error",
                          "groundTruth":  "data1/data/level3/table3_5_generate.png",
                          "output":  "data1/data/seed_1.6_level3/table3_5_generate.png",
                          "analysis":  "During the visual perception stage, the model failed to capture key stylistic attributes, overlooking the bolded line width and prominent marker sizes present in the original chart."
                      },
                      {
                          "title":  "Case 7: table7_5_generate.png",
                          "level":  "Level 3",
                          "levelCode":  "task3",
                          "model":  "seed_1.6_level3",
                          "kind":  "error",
                          "groundTruth":  "data1/data/level3/table7_5_generate.png",
                          "output":  "data1/data/seed_1.6_level3/table7_5_generate.png",
                          "analysis":  "In the generated chart, the histogram bars lack the distinct black borders that were present in the ground truth, which reduces the visual clarity and contrast of the bar distribution, reflecting the model\u0027s failure to reproduce fine-grained visual details."
                      }
                  ]
    },
    {
        "id":  "good-cases-overview",
        "title":  "Good Cases",
        "cases":  [
                      {
                          "title":  "Case 1: errorbar_12.png",
                          "level":  "Level 1",
                          "levelCode":  "task1",
                          "model":  "gemini_3_pro_direct",
                          "kind":  "good",
                          "groundTruth":  "data1/data_good/level1_direct/errorbar_12.png",
                          "output":  "data1/data_good/gemini_3_pro_direct/errorbar_12.png",
                          "analysis":  ""
                      },
                      {
                          "title":  "Case 2: heatmap_7.png",
                          "level":  "Level 1",
                          "levelCode":  "task1",
                          "model":  "gemini_3_pro_direct",
                          "kind":  "good",
                          "groundTruth":  "data1/data_good/level1_direct/heatmap_7.png",
                          "output":  "data1/data_good/gemini_3_pro_direct/heatmap_7.png",
                          "analysis":  ""
                      },
                      {
                          "title":  "Case 3: hist_8.png",
                          "level":  "Level 1",
                          "levelCode":  "task1",
                          "model":  "gemini_3_pro_direct",
                          "kind":  "good",
                          "groundTruth":  "data1/data_good/level1_direct/hist_8.png",
                          "output":  "data1/data_good/gemini_3_pro_direct/hist_8.png",
                          "analysis":  ""
                      },
                      {
                          "title":  "Case 4: pie_4_v4.png",
                          "level":  "Level 2",
                          "levelCode":  "task2",
                          "model":  "gemini_3_pro_level2",
                          "kind":  "good",
                          "groundTruth":  "data1/data_good/level2/pie_4_v4.png",
                          "output":  "data1/data_good/gemini_3_pro_level2/pie_4_v4.png",
                          "analysis":  ""
                      },
                      {
                          "title":  "Case 5: errorpoint_11_v2.png",
                          "level":  "Level 2",
                          "levelCode":  "task2",
                          "model":  "gemini_3_pro_level2",
                          "kind":  "good",
                          "groundTruth":  "data1/data_good/level2/errorpoint_11_v2.png",
                          "output":  "data1/data_good/gemini_3_pro_level2/errorpoint_11_v2.png",
                          "analysis":  ""
                      },
                      {
                          "title":  "Case 6: bar_14_v1.png",
                          "level":  "Level 2",
                          "levelCode":  "task2",
                          "model":  "gemini_3_pro_level2",
                          "kind":  "good",
                          "groundTruth":  "data1/data_good/level2/bar_14_v1.png",
                          "output":  "data1/data_good/gemini_3_pro_level2/bar_14_v1.png",
                          "analysis":  ""
                      },
                      {
                          "title":  "Case 7: table11_2_generate.png",
                          "level":  "Level 3",
                          "levelCode":  "task3",
                          "model":  "gemini_3_pro_level3",
                          "kind":  "good",
                          "groundTruth":  "data1/data_good/level3/table11_2_generate.png",
                          "output":  "data1/data_good/gemini_3_pro_level3/table11_2_generate.png",
                          "analysis":  ""
                      },
                      {
                          "title":  "Case 8: table11_3_generate.png",
                          "level":  "Level 3",
                          "levelCode":  "task3",
                          "model":  "gemini_3_pro_level3",
                          "kind":  "good",
                          "groundTruth":  "data1/data_good/level3/table11_3_generate.png",
                          "output":  "data1/data_good/gemini_3_pro_level3/table11_3_generate.png",
                          "analysis":  ""
                      },
                      {
                          "title":  "Case 9: table1_2_generate.png",
                          "level":  "Level 3",
                          "levelCode":  "task3",
                          "model":  "gemini_3_pro_level3",
                          "kind":  "good",
                          "groundTruth":  "data1/data_good/level3/table1_2_generate.png",
                          "output":  "data1/data_good/gemini_3_pro_level3/table1_2_generate.png",
                          "analysis":  ""
                      }
                  ]
    },
    {
        "id":  "specific-cases-overview",
        "title":  "Specific Cases",
        "cases":  [
                      {
                          "title":  "Case 1: line_19_v4.png",
                          "level":  "Level 2",
                          "levelCode":  "task2",
                          "model":  "claude_level2",
                          "kind":  "specific",
                          "groundTruth":  "data1/data_specific/level2/line_19_v4.png",
                          "output":  "data1/data_specific/claude_level2/line_19_v4.png",
                          "analysis":  "As illustrated, the significantly complex instruction of embedding a box plot inset within a dual-axis line chart exceeds the model\u0027s reasoning capacity; this limitation prevents it from performing valid edits that satisfy the visual context, ultimately resulting in a structurally collapsed inset and severely distorted secondary axis data mapping."
                      },
                      {
                          "title":  "Case 2: scatter_31_v5.png",
                          "level":  "Level 2",
                          "levelCode":  "task2",
                          "model":  "claude_level2",
                          "kind":  "specific",
                          "groundTruth":  "data1/data_specific/level2/scatter_31_v5.png",
                          "output":  "data1/data_specific/claude_level2/scatter_31_v5.png",
                          "analysis":  "The highly complex compound plotting instructions - requiring an inset chart, a Pareto front line, custom markers, and text annotations - overwhelmed the model\u0027s execution capacity, resulting in unimplemented key features (e.g., missing lines and text labels) and partial data loss (e.g., the categorical X-axis being erroneously replaced by arbitrary numerical values)."
                      },
                      {
                          "title":  "Case 3: combination_33_v5.png",
                          "level":  "Level 2",
                          "levelCode":  "task2",
                          "model":  "seed_1.6_level2",
                          "kind":  "specific",
                          "groundTruth":  "data1/data_specific/level2/combination_33_v5.png",
                          "output":  "data1/data_specific/seed_1.6_level2/combination_33_v5.png",
                          "analysis":  "As illustrated by the calibration dashboard, the highly complex composite instructions - which demand cross-plot axis sharing, and data-conditional annotations - overwhelm the model\u0027s logical reasoning and multi-task scheduling capacities; this not only causes a complete collapse of structural layout constraints but also leads to the total omission of crucial analytical visual elements, such as the maximum error highlight."
                      },
                      {
                          "title":  "Case 4: combination_33_v3.png",
                          "level":  "Level 2",
                          "levelCode":  "task2",
                          "model":  "claude_level2",
                          "kind":  "specific",
                          "groundTruth":  "data1/data_specific/level2/combination_33_v3.png",
                          "output":  "data1/data_specific/claude_level2/combination_33_v3.png",
                          "analysis":  "When instructions simultaneously demand dynamic statistical calculations (e.g., binning for means and standard deviations) and rigorous spatial/layering constraints (e.g., absolute coordinate positioning and multiple Z-order configurations), the model suffers a complete layout collapse due to insufficient spatial reasoning. This is evidenced by the wildly disproportionate histogram that obfuscates the core plotting area, highlighting the model\u0027s limitations in complex, multi-task visual rendering."
                      },
                      {
                          "title":  "Case 5: combination_33_v4.png",
                          "level":  "Level 2",
                          "levelCode":  "task2",
                          "model":  "claude_level2",
                          "kind":  "specific",
                          "groundTruth":  "data1/data_specific/level2/combination_33_v4.png",
                          "output":  "data1/data_specific/claude_level2/combination_33_v4.png",
                          "analysis":  "The catastrophic layout failures shown in the figure, including the disconnected CDF axis and missing histogram data, highlight a critical reasoning bottleneck. When confronted with highly reasoning-dependent tasks like reformatting the chart into a complex left-right layout with shared axes, the model fails completely, resulting in an unusable output."
                      },
                      {
                          "title":  "Case 6: table67_4_generate.png",
                          "level":  "Level 3",
                          "levelCode":  "task3",
                          "model":  "gpt_5.2_level3",
                          "kind":  "specific",
                          "groundTruth":  "data1/data_specific/level3/table67_4_generate.png",
                          "output":  "data1/data_specific/gpt_5.2_level3/table67_4_generate.png",
                          "analysis":  "As evidenced by the extensive data blanks in the generated heatmap, processing lengthy raw tabular data heavily occupies the context window capacity, inducing the \"lost-in-the-middle\" phenomenon and ultimately resulting in highly incomplete data extraction."
                      },
                      {
                          "title":  "Case 7: table43_5_generate.png",
                          "level":  "Level 3",
                          "levelCode":  "task3",
                          "model":  "claude_level3",
                          "kind":  "specific",
                          "groundTruth":  "data1/data_specific/level3/table43_5_generate.png",
                          "output":  "data1/data_specific/claude_level3/table43_5_generate.png",
                          "analysis":  "In the generated bubble chart, the model suffered from severe multi-dimensional mapping failure when processing complex data (X, Y, bubble size, and color), not only erroneously altering the linear axis to a logarithmic scale, causing extreme distortion in data distribution, but also completely losing the continuous color mapping."
                      },
                      {
                          "title":  "Case 8: table3_3_generate.png",
                          "level":  "Level 3",
                          "levelCode":  "task3",
                          "model":  "gpt_5.2_level3",
                          "kind":  "specific",
                          "groundTruth":  "data1/data_specific/level3/table3_3_generate.png",
                          "output":  "data1/data_specific/gpt_5.2_level3/table3_3_generate.png",
                          "analysis":  "The sheer volume of the raw tabular data causes severe information attenuation within the context window, resulting in significant categorical omissions and distorted numerical values in the generated chart."
                      },
                      {
                          "title":  "Case 9: table42_5_generate.png",
                          "level":  "Level 3",
                          "levelCode":  "task3",
                          "model":  "claude_level3",
                          "kind":  "specific",
                          "groundTruth":  "data1/data_specific/level3/table42_5_generate.png",
                          "output":  "data1/data_specific/claude_level3/table42_5_generate.png",
                          "analysis":  "The extraordinarily large tabular input coupled with complex plotting instructions caused severe context overload in the model, leading not only to catastrophic data truncation and massive omissions but also to instruction forgetting and complete semantic hallucinations."
                      },
                      {
                          "title":  "Case 10: table42_4_generate.png",
                          "level":  "Level 3",
                          "levelCode":  "task3",
                          "model":  "claude_level3",
                          "kind":  "specific",
                          "groundTruth":  "data1/data_specific/level3/table42_4_generate.png",
                          "output":  "data1/data_specific/claude_level3/table42_4_generate.png",
                          "analysis":  "As illustrated in the generated heatmap, the complex two-dimensional tabular data exceeds the model\u0027s effective context capacity, triggering a severe \u0027lost-in-the-middle\u0027 phenomenon that ultimately results in massive row-level data extraction failures and extensive blank areas."
                      }
                  ]
    }
];

  function el(tag, className, text) {
    const node = document.createElement(tag);
    if (className) node.className = className;
    if (text !== undefined) node.textContent = text;
    return node;
  }

  function escapeHtml(value) {
    return String(value || '').replace(/[&<>"]/g, char => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[char]));
  }

  function normalise(value) {
    return (value || '').toLowerCase();
  }

  function renderFailureCases() {
    const mount = document.getElementById('failure-case-gallery');
    if (!mount) return;

    const allCases = sections.flatMap(section => section.cases.map(item => ({ ...item, sectionId: section.id, sectionTitle: section.title })));
    const errorCount = allCases.filter(item => item.kind === 'error').length;
    const goodCount = allCases.filter(item => item.kind === 'good').length;
    const specificCount = allCases.filter(item => item.kind === 'specific').length;
    const commonSections = sections.filter(section => section.id.startsWith('common-'));
    const goodSection = sections.find(section => section.id === 'good-cases-overview');
    const specificSection = sections.find(section => section.id === 'specific-cases-overview');
    const groups = [
      { id: 'common', label: 'Common Error Cases', count: errorCount },
      { id: 'good', label: 'Good Cases', count: goodCount },
      { id: 'specific', label: 'Specific Cases', count: specificCount }
    ];

    mount.innerHTML = '';

    const intro = el('div', 'failure-intro');
    const copy = el('div', 'failure-copy');
    copy.innerHTML = '<p class="failure-kicker">Failure Case Analysis</p><h2 class="failure-title">Qualitative breakdown of model chart generation behavior</h2><p class="failure-description">This gallery adds detailed case-level analysis to the Chart2Code project page while preserving the original benchmark content. Use the category tabs, level filters, and search box to inspect common errors, successful generations, and task-specific observations.</p>';
    const stats = el('div', 'failure-stats');
    [[allCases.length, 'Total cases'], [errorCount, 'Common errors'], [goodCount, 'Good cases'], [specificCount, 'Specific cases']].forEach(([value, label]) => {
      const stat = el('div', 'failure-stat');
      stat.innerHTML = `<strong>${value}</strong><span>${label}</span>`;
      stats.appendChild(stat);
    });
    intro.append(copy, stats);

    const controls = el('div', 'failure-controls');
    const groupNav = el('div', 'failure-group-nav');
    groups.forEach((group, index) => {
      const btn = el('button', `failure-group-btn${index === 0 ? ' active' : ''}`);
      btn.type = 'button';
      btn.dataset.group = group.id;
      btn.innerHTML = `<span>${escapeHtml(group.label)}</span><b>${group.count}</b>`;
      groupNav.appendChild(btn);
    });

    const subnavWrap = el('div', 'failure-subnav-wrap');
    const subnavLabel = el('div', 'failure-subnav-label', 'Error type');
    const nav = el('div', 'failure-nav');
    commonSections.forEach((section, index) => {
      const btn = el('button', `failure-nav-btn${index === 0 ? ' active' : ''}`);
      btn.type = 'button';
      btn.dataset.section = section.id;
      btn.innerHTML = `<span>${escapeHtml(section.title.replace(' Errors', ''))}</span><b>${section.cases.length}</b>`;
      nav.appendChild(btn);
    });
    subnavWrap.append(subnavLabel, nav);

    const tools = el('div', 'failure-tools');
    const search = el('input', 'failure-search');
    search.type = 'search';
    search.placeholder = 'Search by model, case name, or analysis...';
    search.setAttribute('aria-label', 'Search failure cases');

    const filters = el('div', 'failure-levels');
    [['all', 'All'], ['task1', 'Level 1'], ['task2', 'Level 2'], ['task3', 'Level 3']].forEach(([value, label], index) => {
      const btn = el('button', `failure-filter${index === 0 ? ' active' : ''}`, label);
      btn.type = 'button';
      btn.dataset.level = value;
      filters.appendChild(btn);
    });
    tools.append(search, filters);
    controls.append(groupNav, subnavWrap, tools);

    const summary = el('p', 'failure-result-summary');
    const grid = el('div', 'failure-grid');
    const empty = el('div', 'failure-empty', 'No cases match the current filters.');

    mount.append(intro, controls, summary, grid, empty);

    let activeGroup = 'common';
    let activeSection = commonSections[0]?.id || 'all';
    let activeLevel = 'all';
    let query = '';

    function getGroupSectionIds() {
      if (activeGroup === 'common') return commonSections.map(section => section.id);
      if (activeGroup === 'good' && goodSection) return [goodSection.id];
      if (activeGroup === 'specific' && specificSection) return [specificSection.id];
      return [];
    }

    function renderCards() {
      grid.innerHTML = '';
      const activeSectionIds = getGroupSectionIds();
      const filtered = allCases.filter(item => {
        const matchesGroup = activeSectionIds.includes(item.sectionId);
        const matchesSection = activeGroup !== 'common' || item.sectionId === activeSection;
        const matchesLevel = activeLevel === 'all' || item.levelCode === activeLevel;
        const haystack = normalise(`${item.title} ${item.model} ${item.level} ${item.sectionTitle} ${item.analysis}`);
        return matchesGroup && matchesSection && matchesLevel && haystack.includes(normalise(query));
      });

      const groupLabel = groups.find(group => group.id === activeGroup)?.label || 'Cases';
      const sectionLabel = activeGroup === 'common'
        ? ` / ${commonSections.find(section => section.id === activeSection)?.title || ''}`
        : '';
      summary.textContent = `${groupLabel}${sectionLabel}: ${filtered.length} case${filtered.length === 1 ? '' : 's'} shown`;
      empty.classList.toggle('active', filtered.length === 0);

      filtered.forEach(item => {
        const card = el('article', `failure-card ${item.kind}`);
        const header = el('div', 'failure-card-header');
        const titleWrap = el('div');
        titleWrap.innerHTML = `<p>${escapeHtml(item.sectionTitle)}</p><h3>${escapeHtml(item.title)}</h3>`;
        const badges = el('div', 'failure-badges');
        badges.innerHTML = `<span>${escapeHtml(item.level)}</span><span>${escapeHtml(item.model)}</span>`;
        header.append(titleWrap, badges);

        const images = el('div', 'failure-images');
        [['Ground Truth', item.groundTruth], ['Model Output', item.output]].forEach(([label, src]) => {
          const box = el('figure', 'failure-image-box');
          box.innerHTML = `<figcaption>${label}</figcaption><img loading="lazy" src="${escapeHtml(src)}" alt="${label}: ${escapeHtml(item.title)}">`;
          images.appendChild(box);
        });

        card.append(header, images);
        if (item.kind !== 'good' && item.analysis.trim()) {
          const analysis = el('p', 'failure-analysis');
          analysis.innerHTML = `<strong>Analysis:</strong> ${escapeHtml(item.analysis)}`;
          card.appendChild(analysis);
        }
        grid.appendChild(card);
      });
    }

    groupNav.addEventListener('click', event => {
      const button = event.target.closest('.failure-group-btn');
      if (!button) return;
      activeGroup = button.dataset.group;
      if (activeGroup === 'common' && !commonSections.some(section => section.id === activeSection)) {
        activeSection = commonSections[0]?.id || 'all';
      }
      groupNav.querySelectorAll('.failure-group-btn').forEach(item => item.classList.toggle('active', item === button));
      subnavWrap.hidden = activeGroup !== 'common';
      renderCards();
    });

    nav.addEventListener('click', event => {
      const button = event.target.closest('.failure-nav-btn');
      if (!button) return;
      activeGroup = 'common';
      activeSection = button.dataset.section;
      groupNav.querySelectorAll('.failure-group-btn').forEach(item => item.classList.toggle('active', item.dataset.group === 'common'));
      subnavWrap.hidden = false;
      nav.querySelectorAll('.failure-nav-btn').forEach(item => item.classList.toggle('active', item === button));
      renderCards();
    });

    filters.addEventListener('click', event => {
      const button = event.target.closest('.failure-filter');
      if (!button) return;
      activeLevel = button.dataset.level;
      filters.querySelectorAll('.failure-filter').forEach(item => item.classList.toggle('active', item === button));
      renderCards();
    });

    search.addEventListener('input', event => {
      query = event.target.value;
      renderCards();
    });

    renderCards();
  }

  document.addEventListener('DOMContentLoaded', renderFailureCases);
})();