

#%%
import os, sys
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import numpy as np 
import pkg_resources


from transposonmapper.properties import chromosome_position,gene_aliases
from transposonmapper.processing import chromosome_name_wigfile

from transposonmapper.processing.read_sgdfeatures import sgd_features


from transposonmapper.importing import (
    load_default_files, load_sgd_tab
)


from transposonmapper.processing.dna_features_helpers import (input_region, read_pergene_file, 
                                                              read_wig_file,gene_location)

def dna_features(region, wig_file, pergene_insertions_file, variable="reads", plotting=True, savefigure=False, verbose=True):
    """This scripts takes a user defined genomic region (i.e. chromosome number, region or gene) and creates a dataframe including information about all genomic features in the chromosome (i.e. genes, nc-DNA etc.).
    This can be used to determine the number of reads outside the genes to use this for normalization of the number of reads in the genes.
    Output is a dataframe including major information about all genomic features and optionally a barplot indicating the number of transposons per genomic region.
    A genomic region is here defined as a gene (separated as annotated essential and not essential), telomere, centromere, ars etc.
    This can be used for identifying neutral regions (i.e. genomic regions that, if inhibited, do not influence the fitness of the cells).
    This function can be used for normalizing the transposon insertions per gene using the neutral regions.
    
              
    
    Parameters
    ----------
    region : str
        - Region: e.g. chromosome number (either a normal number between 1 and 16 or in roman numerals between I and XVI), a list like ['V', 0, 14790] which creates a barplot between basepair 0 and 14790) or a genename.

    wig_file : str
        absolute path for the wig file location
    pergene_insertions_file : str 
        asbsoulte path for the _pergene_insertions.txt file location 
    variable : str, optional
        By default "reads". It could be "transposons"or "reads". This would be used for the plotting if True 
    plotting : bool, optional
        Whether or not producing a bar plot with the reads/insertions per genomic location in the region, by default True
    savefigure : bool, optional
        Whether or not saving the plot in the same folder as the datafiles, by default False
    verbose : bool, optional
        Determines how much textual feedback is given. When set to False, only warnings will be shown. By default True

    Outputs
    -------------------
    - dna_df2: Dataframe containing information about the selected chromosome. This includes the following columns:
        - Feature name
        - Standard name of the feature
        - Aliases of feature name (if any)
        - Feature type (e.g. gene, telomere, centromere, etc. If None, this region is not defined)
        - Chromosome
        - Position of feature type in terms of bp relative to chromosome.
        - Length of region in terms of basepairs
        - Number of insertions in region
        - Number of insertions in truncated region where truncated region is the region without the first and last 100bp.
        - Number of reads in region
        - Number of reads in truncated region.
        - Number of reads per insertion (defined by Nreads/Ninsertions)
        - Number of reads per insertion in truncated region (defined by Nreads_truncatedgene/Ninsertions_truncatedgene)
        NOTE: truncated regions are only determined for genes. For the other regions the truncated region values are the same as the non-truncated region values.



    Notes
    ------------------

    Version history:
        1.0: [29-09-2020] First version of this script
        1.1: [14-10-2020] Removed all '..perbp..' colmns in dna_df2 as these can be easily generated using the 'Nbasepairs' column and renamed the following columns
            - all '..gene_central80p..' columns to '..truncatedgene..'
            - 'position' to 'Position'
            - 'Nreadsperbp_normalized' to 'Nreads_normalized'
            - 'Nreadsperbp_central80p_normalized' to 'Nreads_truncatedgene_normalized'
            - 'Nreadsperbp_normalized_byNCregions' to 'Nreads_normalized_byNCregions'
        1.2: [20-10-2020] Removed the normalization since this was outdated.
            
    __Version__: 1.2
    __Date__: 14-10-2020
    __Author__: Gregory van Beek
    """

    # If necessary, load default files
    gff_file, essentials_file, gene_information_file = load_default_files()
    sgd_features_file=load_sgd_tab()

    # Verify presence of files
    data_files = {
        "gff3": gff_file,
        "essentials": essentials_file,
        "gene_names": gene_information_file,
        "sgd_features": sgd_features_file
    }

    for filetype, file_path in data_files.items():
        assert file_path, f"{filetype} not found at {file_path}"


    variable = variable.lower()
    if plotting == True:
        create_plottitle = ''

# DETERMINE INPUTTED REGION

    roi_start,roi_end,region_type,chrom=input_region(region=region,verbose=verbose)

    

#READ WIG FILE FOR GETTING LOCATIONS OF ALL TN INSERTIONS

    insrt_in_chrom_list,reads_in_chrom_list=read_wig_file(wig_file=wig_file,chrom=chrom)


# READ PERGENE_INSERTIONS FILE FOR LOCATION OF ALL INSERTIONS PER EACH GENE.

    gene_position_dict=read_pergene_file(pergene_insertions_file=pergene_insertions_file,chrom=chrom)

# DETERMINE THE LOCATION GENOMIC FEATURES IN THE CURRENT CHROMOSOME AND STORE THIS IN A DICTIONARY

    dna_dict,start_chr,end_chr,len_chr,feature_orf_dict=gene_location(chrom,gene_position_dict,verbose)

## GET FEATURES FROM INTERGENIC REGIONS 

    genomicregions_list = sgd_features(sgd_features_file)[0]

    i = 2
    for genomicregion in genomicregions_list[1:]:
        dna_dict = feature_position(sgd_features(sgd_features_file)[i], chrom, start_chr, dna_dict, genomicregion)
        i += 1


    ### TEST IF ELEMENTS IN FEATURE_ORF_DICT FOR SELECTED CHROMOSOME ARE THE SAME AS THE GENES IN GENE_POSITION_DICT BY CREATING THE DICTIONARY FEATURE_POSITION_DICT CONTAINING ALL THE GENES IN FEATURE_ORF_DICT WITH THEIR CORRESPONDING POSITION IN THE CHROMOSOME
    gene_alias_dict = gene_aliases(gene_information_file)[0]
    orf_position_dict = {}
    for feature in feature_orf_dict:
        if feature_orf_dict.get(feature)[5] == chrom:
            if feature in gene_position_dict:
                orf_position_dict[feature] = [feature_orf_dict.get(feature)[6], feature_orf_dict.get(feature)[7]]
            else:
                for feature_alias in gene_alias_dict.get(feature):
                    if feature_alias in gene_position_dict:
                        orf_position_dict[feature_alias] = [feature_orf_dict.get(feature)[6], feature_orf_dict.get(feature)[7]]



    if sorted(orf_position_dict) == sorted(gene_position_dict):
        if verbose == True:
            print('Everything alright, just ignore me!')
        
    else:
        print('WARNING: Genes in feature_list are not the same as the genes in the gene_position_dict. Please check!')


    del (sgd_features_file, feature_orf_dict, orf_position_dict, feature, feature_alias, gene_position_dict)

## DETERMINE THE NUMBER OF TRANSPOSONS PER BP FOR EACH FEATURE

    reads_loc_list = [0] * len(dna_dict) # CONTAINS ALL READS JUST LIKE READS_IN_CHROM_LIST, BUT THIS LIST HAS THE SAME LENGTH AS THE NUMBER OF BP IN THE CHROMOSOME WHERE THE LOCATIONS WITH NO READS ARE FILLED WITH ZEROS
    i = 0
    for ins in insrt_in_chrom_list:
        reads_loc_list[ins] = reads_in_chrom_list[i]
        i += 1


    del (i, ins, insrt_in_chrom_list, reads_in_chrom_list)#, dna_df)

## CREATE DATAFRAME FOR EACH FEATURE (E.G. NONCODING DNA, GENE, ETC.) IN THE CHROMOSOME AND DETERMINE THE NUMBER OF INSERTIONS AND READS PER FEATURE.

    feature_NameAndType_list = []
    f_previous = dna_dict.get(start_chr)[0]
    f_type = dna_dict.get(start_chr)[1]
    N_reads = []
    N_reads_list_true=[]
    N_reads_list = []
    N_reads_truncatedgene_list = []
    N_insrt_truncatedgene_list = []
    N_insrt_list = []
    N_bp = 1
    N_bp_list = []
    f_start = 0
    f_end = 0
    f_pos_list = []
    i = 0
    for bp in dna_dict:
        f_current = dna_dict.get(bp)[0]
        if f_current == f_previous:
            f_type = dna_dict.get(bp)[1]
            f_end += 1
            N_bp += 1
            N_reads.append(reads_loc_list[i])
        elif (f_current != f_previous or (i+start_chr) == end_chr):# and not f_current.endswith('-A'):
            feature_NameAndType_list.append([f_previous, f_type])
            N_reads_list.append(sum(N_reads))
            N_reads_list_true.append(np.array(N_reads,dtype=float))
            N_insrt_list.append(len([ins for ins in N_reads if not ins == 0]))
            if not f_type == None and f_type.startswith('Gene'):
                N10percent = 100#int(len(N_reads) * 0.1) #TRUNCATED GENE DEFINITION
                N_reads_truncatedgene_list.append(sum(N_reads[N10percent:-N10percent]))
                N_insrt_truncatedgene_list.append(len([ins for ins in N_reads[N10percent:-N10percent] if not ins == 0]))
            else:
                N_reads_truncatedgene_list.append(sum(N_reads))
                N_insrt_truncatedgene_list.append(len([ins for ins in N_reads if not ins == 0]))

            N_bp_list.append(N_bp)
            N_reads = []
            N_bp = 1
            f_pos_list.append([f_start, f_end+f_start])
            f_start = f_start + f_end + 1
            f_end = 0
            f_previous = f_current
        i += 1

    N_reads_per_ins_list = []
    N_reads_per_ins_truncatedgene_list = []
    for i in range(len(N_reads_list)):
        if N_insrt_list[i] < 5:
            N_reads_per_ins_list.append(0)
            N_reads_per_ins_truncatedgene_list.append(0)
        elif N_insrt_truncatedgene_list[i] < 5:
            N_reads_per_ins_list.append(N_reads_list[i]/(N_insrt_list[i]-1))
            N_reads_per_ins_truncatedgene_list.append(0)
        else:
            N_reads_per_ins_list.append(N_reads_list[i]/(N_insrt_list[i]-1))
            N_reads_per_ins_truncatedgene_list.append(N_reads_truncatedgene_list[i]/N_insrt_truncatedgene_list[i])


    #############get all essential genes together with their aliases##############
    with open(essentials_file, 'r') as f:
        essentials_temp_list = f.readlines()[1:]
    essentials_list = [essential.strip('\n') for essential in essentials_temp_list]
    del essentials_temp_list

    gene_alias_dict = gene_aliases(gene_information_file)[0]
    for key, val in gene_alias_dict.items():
        if key in essentials_list:
            for alias in val:
                essentials_list.append(alias)

    #ADD
    essentiality_list = []
    for feature in feature_NameAndType_list:
        if not feature[0] == "noncoding":
            if feature[1] in genomicregions_list:
                essentiality_list.append(None)
            elif feature[0] in essentials_list:
                essentiality_list.append(True)
            else:
                essentiality_list.append(False)
        else:
            essentiality_list.append(None)

    del (key, val, alias, essentials_list, feature, gene_information_file)#, gene_alias_dict)#, reads_loc_list)
    ##############################################################################

    feature_name_list = []
    feature_type_list = []
    feature_alias_list = []
    feature_standardname_list = []
    for feature_name in feature_NameAndType_list:
        feature_name_list.append(feature_name[0])
        feature_type_list.append(feature_name[1])
        if feature_name[1] != None and feature_name[1].startswith('Gene') and feature_name[0] in gene_alias_dict:
            if gene_alias_dict.get(feature_name[0])[0] == feature_name[0]:
                feature_standardname_list.append(feature_name[0])
                feature_alias_list.append('')
            else:
                if len(gene_alias_dict.get(feature_name[0])) > 1:
                    feature_standardname_list.append(gene_alias_dict.get(feature_name[0])[0])
                    feature_alias_list.append(gene_alias_dict.get(feature_name[0])[1:])
                else:
                    feature_standardname_list.append(gene_alias_dict.get(feature_name[0])[0])
                    feature_alias_list.append('')
        else:
            feature_standardname_list.append(feature_name[0])
            feature_alias_list.append('')


    all_features = {'Feature_name': feature_name_list,
                    'Standard_name': feature_standardname_list,
                    'Feature_alias':feature_alias_list,
                    'Feature_type': feature_type_list,
                    'Essentiality': essentiality_list,
                    'Chromosome': [chrom]*len(feature_name_list),
                    'Position': f_pos_list,
                    'Nbasepairs':N_bp_list,
                    'Ninsertions':N_insrt_list,
                    'Ninsertions_truncatedgene':N_insrt_truncatedgene_list,
                    'Nreads':N_reads_list,
                    'Nreads_list':  N_reads_list_true,
                    'Nreads_truncatedgene':N_reads_truncatedgene_list,
                    'Nreadsperinsrt':N_reads_per_ins_list,
                    'Nreadsperinsrt_truncatedgene':N_reads_per_ins_truncatedgene_list}


    dna_df2 = pd.DataFrame(all_features, columns = [column_name for column_name in all_features]) #search for feature using: dna_df2.loc[dna_df2['Feature'] == 'CDC42']
    #CREATE NEW COLUMN WITH ALL DOMAINS OF THE GENE (IF PRESENT) AND ANOTHER COLUMN THAT INCLUDES LISTS OF THE BP POSITIONS OF THESE DOMAINS


    #PRINT INFORMATION FOR THE SELECTED GENE
    if region_type == 'Gene':
        for region_info in dna_df2.itertuples():
            if region_info.Feature_name == region.upper() or region_info.Standard_name == region.upper():
                print(region_info)


    del (dna_dict, feature_NameAndType_list, feature_name_list, feature_type_list, feature_name, f_type, f_previous, f_start, f_end, f_pos_list, f_current, N_reads, N_reads_list, N_insrt_list, N_reads_truncatedgene_list, N_insrt_truncatedgene_list, N10percent, N_bp, N_bp_list, bp, i, start_chr, end_chr, all_features, essentiality_list, essentials_file, genomicregions_list)


# CREATE BAR PLOT
    if plotting == True:
        create_plottitle = region
        region_type = 'Gene'
    if plotting == True:
        noncoding_color = "#002538"
        essential_color = "#10e372"
        nonessential_color = "#d9252e"
        codingdna_color = '#29a7e6'
        textcolor = "#000000"
        textsize = 14


        feature_middle_pos_list = []
        sum_bp = 0
        for x in dna_df2['Nbasepairs']:
            feature_middle_pos_list.append(x/2 + sum_bp)
            sum_bp += x
        del (x, sum_bp)

        feature_width_list = list(dna_df2['Nbasepairs'])


        barcolor_list = []
        for feature in dna_df2['Feature_name']:
            if feature == 'noncoding':
                barcolor_list.append(noncoding_color)
            elif dna_df2.loc[dna_df2['Feature_name'] == feature]['Essentiality'].iloc[0] == False:
                barcolor_list.append(nonessential_color)
            elif dna_df2.loc[dna_df2['Feature_name'] == feature]['Essentiality'].iloc[0] == True:
                barcolor_list.append(essential_color)
            elif dna_df2.loc[dna_df2['Feature_name'] == feature]['Essentiality'].iloc[0] == None:
                barcolor_list.append(codingdna_color)
        del (feature)




        ###PLOTTING
        plt.figure(figsize=(19,9))
        grid = plt.GridSpec(20, 1, wspace=0.0, hspace=0.01)


        ax = plt.subplot(grid[0:19,0])
        if variable == "insertions":
            ax.bar(feature_middle_pos_list, list(dna_df2['Ninsertions']), feature_width_list, color=barcolor_list)
            ax.set_ylabel("Transposons per region", fontsize=textsize, color=textcolor)
        elif variable == "reads":
            ax.bar(feature_middle_pos_list, list(dna_df2['Nreads']), feature_width_list, color=barcolor_list)
            ax.set_ylabel("Reads per region", fontsize=textsize, color=textcolor)


        if roi_start != None and roi_end != None and roi_start < len_chr and roi_end < len_chr:
            ax.set_xlim(roi_start, roi_end)
        else:
            ax.set_xlim(0, len_chr)

        ax.grid(linestyle='-', alpha=1.0)
        ax.tick_params(labelsize=textsize)
    #    ax.set_xticklabels([])
        ax.tick_params(axis='x', which='major', pad=30)
        ax.ticklabel_format(axis='x', style='sci', scilimits=(0,0))
        ax.xaxis.get_offset_text().set_fontsize(textsize)
        ax.set_xlabel("Basepair position on chromosome "+chrom, fontsize=textsize, color=textcolor, labelpad=10)
        ax.set_title(create_plottitle, fontsize=textsize, color=textcolor)
        legend_noncoding = mpatches.Patch(color=noncoding_color, label="Noncoding DNA")
        legend_essential = mpatches.Patch(color=essential_color, label="Annotated essential genes")
        legend_nonessential = mpatches.Patch(color=nonessential_color, label="Nonessential genes")
        legend_coding = mpatches.Patch(color=codingdna_color, label="Other genomic regions")
        leg = ax.legend(handles=[legend_noncoding, legend_essential, legend_nonessential, legend_coding]) #ADD
        for text in leg.get_texts():
            text.set_color(textcolor)
        del text

        axc = plt.subplot(grid[19,0])

        l = 0
        counter = 0
        for width in feature_width_list:
            if dna_df2.loc[counter][4] == True:
                axc.axvspan(l,l+width,facecolor=essential_color,alpha=0.3)
            elif dna_df2.loc[counter][4] == False and not dna_df2.loc[counter][0] == 'noncoding':
                axc.axvspan(l,l+width,facecolor=nonessential_color,alpha=0.3)
            elif dna_df2.loc[counter][4] == None and not dna_df2.loc[counter][0] == 'noncoding':
                axc.axvspan(l,l+width,facecolor=codingdna_color,alpha=0.5)
            l += width
            counter += 1
        if roi_start != None and roi_end != None and roi_start < len_chr and roi_end < len_chr:
            axc.set_xlim(roi_start, roi_end)
        else:
            axc.set_xlim(0, len_chr)
        axc.tick_params(labelsize=textsize)
        axc.set_yticklabels([])
        axc.tick_params(
            axis='x',          # changes apply to the x-axis
            which='both',      # both major and minor ticks are affected
            bottom=False,      # ticks along the bottom edge are off
            top=False,         # ticks along the top edge are off
            labelbottom=False) # labels along the bottom edge are off

        axc.tick_params(
            axis='y',          # changes apply to the y-axis
            which='both',      # both major and minor ticks are affected
            left=False,        # ticks along the bottom edge are off
            right=False,       # ticks along the top edge are off
            labelleft=False)   # labels along the bottom edge are off


        if savefigure == True:
            file_dirname=pkg_resources.resource_filename("transposonmapper", "data_files/")
            if variable == 'reads':
                saving_name = os.path.join(file_dirname,'GenomicFeaturesReads_Barplot_Chrom'+chrom+'_NonNormalized')
            else:
                saving_name = os.path.join(file_dirname,'GenomicFeaturesInsertions_Barplot_Chrom'+chrom+'_NonNormalized')
            plt.savefig(saving_name, orientation='landscape', dpi=200)
            plt.close()

        del (barcolor_list, codingdna_color, essential_color, feature_middle_pos_list, feature_width_list, noncoding_color, nonessential_color, textcolor, textsize, l, counter, width)


## RETURN STATEMENT
    return(dna_df2)




def feature_position(feature_dict, chrom, start_chr, dna_dict, feature_type=None):
    
    position_dict = {}
    for feat in feature_dict:
        if feature_dict.get(feat)[5] == chrom:
#            if feat.startswith("TEL") and feat.endswith('L'): #correct for the fact that telomeres at the end of a chromosome are stored in the reverse order.
            if int(feature_dict.get(feat)[6]) > int(feature_dict.get(feat)[7]):
                position_dict[feat] = [feature_dict.get(feat)[5], feature_dict.get(feat)[7], feature_dict.get(feat)[6]]
            else:
                position_dict[feat] = [feature_dict.get(feat)[5], feature_dict.get(feat)[6], feature_dict.get(feat)[7]]


    for feat in position_dict:
        for bp in range(int(position_dict.get(feat)[1])+start_chr, int(position_dict.get(feat)[2])+start_chr):
            if dna_dict[bp] == ['noncoding', None]:
                dna_dict[bp] = [feat, feature_type]
            else:
#                print('Bp %i is already occupied by %s' % (bp, str(dna_dict.get(bp))))
                pass


    return(dna_dict)



# #%% INPUT

# # for chrom in ['I', 'II', 'III', 'IV', 'V', 'VI', 'VII', 'VIII', 'IX', 'X', 'XI', 'XII', 'XIII', 'XIV', 'XV', 'XVI']:
# #     region=chrom

# region = 1 #e.g. 1, "I", ["I", 0, 10000"], gene name (e.g. "CDC42")
# wig_file = r""
# pergene_insertions_file = r""
# plotting=True
# variable="reads" #"reads" or "insertions"
# savefigure=False
# verbose=True

# if __name__ == '__main__':
#     dna_df2 = dna_features(region=region,
#                  wig_file=wig_file,
#                  pergene_insertions_file=pergene_insertions_file,
#                  variable=variable,
#                  plotting=plotting,
#                  savefigure=savefigure,
#                  verbose=verbose)


# %%
