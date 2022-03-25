###################################
## BC overlap bweteen replicates ##
###################################


rule statistic_overlapBCs:
    conda:
        "../../envs/r.yaml"
    input:
        files=lambda wc: expand(
            getFinalCounts(wc.project, wc.config, wc.type, wc.raw_or_assigned),
            project=wc.project,
            condition=wc.condition,
            config=wc.config,
            replicate=getReplicatesOfCondition(wc.project, wc.condition),
        ),
        script="../workflow/scripts/count/BCCounts_betweenReplicates.R",
    output:
        "results/experiments/{project}/stats/{raw_or_assigned}/overlapBCandCounts_{condition}_{type}_{config}.tsv",
    params:
        input=lambda wc: ",".join(
            expand(
                getFinalCounts(wc.project, wc.config, wc.type, wc.raw_or_assigned),
                project=wc.project,
                condition=wc.condition,
                config=wc.config,
                replicate=getReplicatesOfCondition(wc.project, wc.condition),
            )
        ),
        cond="{condition}_{type}",
        replicates=lambda wc: ",".join(
            getReplicatesOfCondition(wc.project, wc.condition)
        ),
    log:
        "logs/experiments/{project}/stats/{raw_or_assigned}/statistic_overlapBCs.{condition}_{type}_{config}.log",
    shell:
        """
        Rscript {input.script} \
        --outfile {output} \
        --condition {params.cond} \
        --files {params.input} --replicates {params.replicates} > {log}
        """


rule statistic_combine_overlapBCs_stats_raw:
    conda:
        "../../envs/default.yaml"
    input:
        stats=lambda wc: expand(
            "results/experiments/{{project}}/stats/counts/overlapBCandCounts_{condition}_{type}_{config}.tsv",
            type=["DNA", "RNA"],
            condition=getConditions(wc.project),
            config=wc.config,
        ),
    output:
        report(
            "results/experiments/{project}/stats/statistic_overlapBCs_counts_{config}.tsv",
            caption="../../report/bc_overlap.rst",
            category="{project}",
            subcategory="Barcodes",
        ),
    log:
        "logs/experiments/{project}/stats/statistic_combine_overlapBCs_stats_raw.{config}.log",
    shell:
        """
        set +o pipefail;
        (
            cat {input.stats[0]} | head -n 1;
            for i in {input.stats}; do
                cat $i | tail -n +2
            done;
        ) > {output}
        """


rule statistic_combine_overlapBCs_stats_assigned:
    conda:
        "../../envs/default.yaml"
    input:
        stats=lambda wc: expand(
            "results/experiments/{{project}}/stats/assigned_counts/{{assignment}}/overlapBCandCounts_{condition}_{type}_{{config}}.tsv",
            type=["DNA", "RNA"],
            condition=getConditions(wc.project),
        ),
    output:
        report(
            "results/experiments/{project}/stats/statistic_overlapBCs_assigned_counts_{assignment}_{config}.tsv",
            caption="../../report/bc_overlap_assignment.rst",
            category="{project}",
            subcategory="Barcodes",
        ),
    log:
        "logs/experiments/{project}/stats/statistic_combine_overlapBCs_stats_assigned.{assignment}_{config}.log",
    shell:
        """
        set +o pipefail;
        (
            cat {input.stats[0]} | head -n 1;
            for i in {input.stats}; do
                cat $i | tail -n +2
            done;
        ) > {output}
        """
