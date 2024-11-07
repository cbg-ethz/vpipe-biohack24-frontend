import matplotlib.pyplot as plt
import pandas as pd
import yaml
import boto3
import seaborn as sns
import matplotlib.pyplot as plt
import streamlit as st

def app():
    # Streamlit title and description
    st.title('Identifing Mutations Arising')
    st.write('Visualizing the frequency of mutations arising')
    

    # Access AWS credentials from secrets management
    AWS_ACCESS_KEY_ID = st.secrets["aws"]["AWS_ACCESS_KEY_ID"]
    AWS_SECRET_ACCESS_KEY = st.secrets["aws"]["AWS_SECRET_ACCESS_KEY"]
    AWS_DEFAULT_REGION = st.secrets["aws"]["AWS_DEFAULT_REGION"]


    # Create an S3 client
    s3 = boto3.client(
        "s3",
        aws_access_key_id=AWS_ACCESS_KEY_ID,
        aws_secret_access_key=AWS_SECRET_ACCESS_KEY,
        region_name=AWS_DEFAULT_REGION, 

    )

    bucket_name = 'vpipe-output'
    kp3_mutations = 'mut_def/kp23.yaml'
    xec_mutations = "mut_def/xec.yaml"


    @st.cache_data  # Cache the data for better performance
    def load_yaml_from_s3(bucket_name, file_name):
        """Loads YAML data from an S3 bucket.
        
        Args:
            bucket_name (str): The name of the S3 bucket.
            file_name (str): The name of the file to load, including the path.
                            also called object key.
        """
        try:
            obj = s3.get_object(Bucket=bucket_name, Key=file_name)
            data = yaml.safe_load(obj["Body"])
            return data
        except Exception as e:
            st.error(f"Error loading YAML from S3: {e}")
            return None
        

    @st.cache_data  # Cache the data for better performance
    def load_tsv_from_s3(bucket_name, file_name):
        """Loads tsv data from an S3 bucket.
        
        Args:
            bucket_name (str): The name of the S3 bucket.
            file_name (str): The name of the file to load, including the path.
                            also called object key.
        """
        try:
            obj = s3.get_object(Bucket=bucket_name, Key=file_name)
            if file_name.endswith('.gz'):
                data = pd.read_csv(obj['Body'], sep='\t', compression='gzip')
            else:
                data = pd.read_csv(obj['Body'], sep='\t')
            return data
        except Exception as e:
            st.error(f"Error loading tsv from S3: {e}")
            return None


    # Load the YAML data from S3
    kp3_mutations_data = load_yaml_from_s3(bucket_name, kp3_mutations)
    xec_mutations_data = load_yaml_from_s3(bucket_name, xec_mutations)

    # Load the selected mutations tally
    tallymut = load_tsv_from_s3(bucket_name, 'subset_tallymut.tsv.gz')


    @st.cache_data  # Cache the data for better performance
    def filter_for_variant(tally, variant):
            # Extract the positions and mutations from kp3_df
            kp3_positions = variant.index
            kp3_mutations = variant['mut'].str[-1]

            # Filter new_df based on the positions and mutations in kp3_df
            filtered_df = tally[tally.apply(lambda row: row['pos'] in kp3_positions and row['base'] == kp3_mutations.get(row['pos']), axis=1)]

            return filtered_df

    @st.cache_data  # Cache the data for better performance
    def plot_heatmap(data, title='Heatmap of Fractions by Date and Position', xlabel='Date', ylabel='Position', figsize=(20, 10), num_labels=20, location=''):
        
        # Pivot the dataframe to get the desired format for the heatmap 
        heatmap_data = data.pivot_table(index='pos', columns='date', values='frac')

        # Create the heatmap
        plt.figure(figsize=figsize)
        # Create a custom colormap to highlight NaN values with a different color
        cmap = sns.color_palette("Blues", as_cmap=True)
        cmap.set_bad(color='pink')

        # Create the heatmap with the custom colormap
        sns.heatmap(heatmap_data, cmap=cmap, cbar_kws={'label': 'Fraction'}, mask=heatmap_data.isna())

        plt.title(title)
        plt.xlabel(xlabel)
        plt.ylabel(ylabel)

        # Limit the date labels to fit nicely
        xticks = plt.xticks()
        plt.xticks(ticks=xticks[0][::len(xticks[0]) // num_labels], labels=[xticks[1][i] for i in range(0, len(xticks[1]), len(xticks[1]) // num_labels)], rotation=60)

        plt.yticks(rotation=0)
        plt.tight_layout()

        # Display the plot in Streamlit
        st.pyplot(plt)


    def filter_by_location(data, location):
        return data[data['location'] == location]

    # Dropdown to select a location
    locations = [
        'Lugano (TI)',
        'Zürich (ZH)',
        'Chur (GR)',
        'Altenrhein (SG)',
        'Laupen (BE)',
        'Genève (GE)',
        'Basel (BS)',
        'Luzern (LU)'
    ]

    selected_location = st.selectbox('Select a location', locations)

    # Dataset selection
    selected_dataset = st.selectbox('Select Dataset', ['kp3/kp2', 'xec'])  # Replace with your dataset names


    if st.button('Plot Heatmap'):
        if selected_dataset == 'kp3/kp2':
            plot_heatmap(
                filter_by_location(
                     filter_for_variant(
                                tallymut,
                                pd.DataFrame(kp3_mutations_data)
                                ),
                    location=selected_location
                    ),
                title='kp3/kp2 Heatmap',
                location=selected_location
                )
        elif selected_dataset == 'xec':
                plot_heatmap(
                    filter_by_location(
                         filter_for_variant(
                                tallymut, pd.DataFrame(xec_mutations_data)
                            ),  
                        location=selected_location
                        ),
                    title='xec Heatmap',
                    location=selected_location
                    ) 