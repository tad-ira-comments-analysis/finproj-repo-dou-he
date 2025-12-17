## Text As Data Final Project: An Analysis of US Legislative Focus Through Public Comment Text

Puran Dou (@PRDough, email: pd757@georgetown.edu) & Yuyan He (@yuyanhe0202, email: yh915@georgetown.edu)


#### Citation

Waight, Henry, Solomon Messing, Anton Shirikov, Margaret E. Roberts, Jonathan Nagler, Jeff Greenfield, Marshall A. Brown, Kevin Aslett, and Joshua A. Tucker. 2025. “Quantifying Narrative Similarity Across Languages.” *Sociological Methods & Research* 54 (3): 933–983. https://doi.org/10.1177/00491241251340080.

Federal Chief Data Officer Council. 2021. *Implementing Federal-Wide Comment Analysis Tools*. resources.data.gov. Accessed December 17, 2025. https://resources.data.gov/resources/cdoc_comment_analysis/.

Ortakci, Yasin, and Burak Borhan. 2025. “Optimizing SBERT for Long Text Clustering: Two Novel Approaches with Empirical Insights.” *The Journal of Supercomputing* 81 (Article 950). Published June 2, 2025. https://doi.org/10.1007/s11227-025-07414-4.


#### Repository Contents

This repository contains the following folders:

-   `data`
-   `scripts`
-   `output`
-   `presentation`
-   `paper`

Descriptions of folder contents can be found below.

#### data

This folder contains the data used for this study. This folder was not pushed due to file size. Full data could be accessed through the Box link below:
https://georgetown.box.com/s/jmrxsfksdzvtbf62gs7r3cxs0g39b9yk

-  `raw_data_healthcare.csv`: merged and cleaned raw healthcare comments data downloaded from Regulations.gov
-  `dbscan_healthcare_unique.csv`: unique healthcare comments after dbscan de-duplication used for LDA
-  `dbscan_healthcare_cluster_representatives.csv`: repetitive representatives of healthcare after dbscan de-duplication used for LDA comparison
-  `dbscan_healthcare_combined.csv`: healthcare comments combined unique and repetitive representatives used for Wordfish

-  `raw_data_energy.csv`: merged and cleaned raw energy comments data downloaded from Regulations.gov
-  `dbscan_energy_unique.csv`: unique energy comments after dbscan de-duplication used for LDA
-  `dbscan_energy_cluster_representatives.csv`: repetitive representatives of energy after dbscan de-duplication used for LDA comparison
-  `dbscan_energy_combined.csv`: energy comments combined unique and repetitive representatives used for Wordfish


#### scripts

This folder contains all `.qmd`, `.py`, and `.ipynb` files used for the final project. Scripts are organized into three subfolders:

- `scraping_clean_combine/`
  - `01_scrape_docket_metadata_and_pdfs.py`: Scrapes docket metadata and PDFs from Regulations.gov and outputs raw scraped files for downstream processing.
  - `02_combine_clean_ira_comments.py`: Combines and cleans scraped IRA comments into an analysis-ready dataset (CSV) used for embedding, clustering, topic modeling, and scaling.

- `embedding_dbscan/`
  - `ira_comments_embed_dbscan_postprocess.ipynb`: Computes SBERT embeddings on comment text, performs DBSCAN clustering, and post-processes outputs (e.g., cluster labels and de-duplicated datasets) for LDA/Wordfish analysis.

- `lda_wordfish/`
  - `energy_lda.qmd`: Runs LDA topic modeling for the Env/Energy (IRS) corpus and produces topic summaries/figures.
  - `energy_wordfish_bootlegger_baptist_analysis.qmd`: Runs Wordfish scaling and analyzes the Bootlegger–Baptist dimension for the Env/Energy docket(s), producing Wordfish figures and interpretation outputs.
  - `healthcare_lda_wordfish.qmd`: Runs LDA topic modeling and Wordfish scaling for the healthcare corpus, producing topic and Wordfish outputs/figures.


#### output

This folder contains all `.png` figures produced in the analysis:

-  `lda_choosek.png`: Plot used for choosing the number of topics (K) for LDA; was produced using `healthcare_lda_wordfish.qmd`.
-  `healthcare_wordfish.png`: Wordfish results/figure for the healthcare corpus; was produced using `healthcare_lda_wordfish.qmd`.
-  `energy_wordfish_irs20230042.png`: Wordfish results/figure for the Env/Energy (IRS-2023-0042) docket; was produced using `energy_wordfish_bootlegger_baptist_analysis.qmd`.
-  `energy_wordfish_irs20230066.png`: Wordfish results/figure for the Env/Energy (IRS-2023-0066) docket; was produced using `energy_wordfish_bootlegger_baptist_analysis.qmd`.


#### presentation

This folder contains the PDF of the final project presentation, delivered for Georgetown’s PPOL 6801: Text as Data – Computational Linguistics.

#### paper

This folder contains the final project report, submitted for grading for Georgetown's PPOL 6801: Text as Data - Computational Linguistics
