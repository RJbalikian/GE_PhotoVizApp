import codecs
import traceback

import numpy as np
import pandas as pd
import pyproj
from pyproj.database import query_utm_crs_info

import streamlit as st

CRS_LIST = pyproj.database.query_crs_info()
CRS_STR_LIST = [f"{crs.auth_name}:{crs.code} - {crs.name}" for crs in CRS_LIST]
CRS_DICT = {f"{crs.auth_name}:{crs.code} - {crs.name}": crs for crs in CRS_LIST}
DEFAULT_POINTS_CRS = "EPSG:4326 - WGS 84"
DEFAULT_POINTS_CRS_INDEX = CRS_STR_LIST.index(DEFAULT_POINTS_CRS)

st.set_page_config(layout='wide')


def main():
    mainContainer = st.session_state.main_container = st.container()
    if hasattr(st.session_state, 'image_file'):
        if hasattr(st.session_state.image_file, 'name'):
            mainContainer.image(st.session_state.image_file, caption=st.session_state.image_file.name, width='stretch')

    if hasattr(st.session_state, 'df'):
        mainContainer.dataframe(st.session_state.df)

    with st.sidebar:
        st.title("GE 3D Image Visualization")

        st.file_uploader('Upload Image File',
                         key='image_file',
                         on_change=show_image)

        st.text_area('Copy/paste table with location values',
                     key='table_text',
                     on_change=parse_table_text)
        st.checkbox('Data Includes Header',
                    value=True,
                    key='includes_header')
        lineSepCol, itemSepCol = st.columns([0.5, 0.5])
        lineSepCol.text_input('Line Separator',
                              value=r'\n',
                              key='line_sep')

        itemSepCol.text_input('Item Separator',
                              value=r'\t',
                              key='item_sep')

        st.session_state.lineSep = st.session_state.line_sep
        if st.session_state.lineSep[0] == r'\blah'[0]:
            st.session_state.lineSep = codecs.decode(st.session_state.lineSep,
                                                     'unicode_escape')

        st.session_state.itemSep = st.session_state.item_sep
        if st.session_state.itemSep[0] == r'\blah'[0]:
            st.session_state.itemSep = codecs.decode(st.session_state.itemSep,
                                                     'unicode_escape')

        xColOpts = ['X']
        yColOpts = ['Y']
        distOpts = ['Distance']
        xColInd = yColInd = distColInd = 0
        xColName = xColOpts[0]
        yColName = yColOpts[0]
        distColName = distOpts[0]

        if hasattr(st.session_state, 'dataColumns'):
            xColList = ["x", 'utme', 'utmeasting', 'easting', 'east', 'e',
                        'xcoord', 'long', 'lon', 'longitude']
            yColList = ["y", 'utmn', 'utmnorthing', 'northing', 'north', 'n',
                        'ycoord', 'lat', 'latitude']
            distList = ['dist', 'xdist', 'xdistm', 'xdist_m', 'distance',
                        'xdistance', 'xdistancem', 'xdistance_m']
            xColOpts = yColOpts = distOpts = st.session_state.dataColumns

            for i, col in enumerate(st.session_state.dataColumns):
                xCond1 = str(col).lower() in xColList 
                xCond2 = 'east' in str(col).lower()

                yCond1 = str(col).lower() in yColList
                yCond2 = 'north' in str(col).lower()
                yCond3 = 'y' in str(col).lower()

                distCond1 = col.lower() in distList
                distCond2 = 'dist' in str(col).lower()

                if xCond1 or xCond2:
                    xColInd = i
                    xColName = col
                elif yCond1 or yCond2 or yCond3:
                    yColInd = i
                    yColName = col
                elif distCond1 or distCond2:
                    distColInd = i
                    distColName = col

            try:
                st.session_state.df[xColName] = pd.to_numeric(st.session_state.df[xColName], errors='coerce')
                st.session_state.df[yColName] = pd.to_numeric(st.session_state.df[yColName], errors='coerce')
                st.session_state.df[distColName] = pd.to_numeric(st.session_state.df[distColName], errors='coerce')

            except Exception:
                traceback.print_exc()
                st.write("Could not update all columns")

        xColCol, yColCol, distCol = st.columns([0.5, 0.5, 0.5])
        xColCol.selectbox("Select X Column",
                          options=xColOpts,
                          index=xColInd,
                          key='x_column')
        yColCol.selectbox("Select Y Column",
                          options=yColOpts,
                          index=yColInd,
                          key='y_column')
        distCol.selectbox("Select Distance Column",
                          options=distOpts,
                          index=distColInd,
                          key='dist_column'
                          )
        st.selectbox('CRS of Data Coordinates',
                     options=CRS_STR_LIST,
                     index=DEFAULT_POINTS_CRS_INDEX,
                     key='input_crs')

        st.button('Generate 3D KML Visualization',
                  type='primary',
                  on_click=generate_kml,
                  key='generate_kml_button')


def parse_table_text():
    tableTextIN = st.session_state.table_text

    lineTable = tableTextIN.split(st.session_state.lineSep)
    tableData = [lineStr.split(st.session_state.itemSep) for lineStr in lineTable]
    if st.session_state.includes_header:
        st.session_state.dataColumns = tableData[0]
        tableData = tableData[1:]
    else:
        st.session_state.dataColumns = np.arange(len(tableData[0]))
    st.session_state.df = pd.DataFrame(tableData,
                                       columns=st.session_state.dataColumns)
    st.session_state.df = st.session_state.df.dropna(how='any', axis=0)
    #st.dataframe(st.session_state.df)
    #if hasattr(st.session_state.image_file, 'name'):
    #    st.image(st.session_state.image_file, caption=st.session_state.image_file.name, width='stretch')

def get_crs_info():
    import webbrowser
    crscode = st.session_state.crs_info_select.split(":")[1].split(" ")[0]
    webbrowser.open(f"https://epsg.io/?q={crscode}")


def generate_kml():

    # Initialize variables
    kmlTemplateFile = r"TEMPLATE_ERT_GoogleEarthBillboard.kml"
    df = st.session_state.df
    xCol = st.session_state.x_column
    yCol = st.session_state.y_column
    xDistCol = st.session_state.dist_column

    viewHeight = 100
    viewAngle = 26.5

    # Get initial information
    xDist = abs(df[xDistCol].max() - df[xDistCol].min())
    centerX = round(df[xCol].mean(), 2)
    centerY = round(df[yCol].mean(), 2)
    points_crs = CRS_DICT[st.session_state.input_crs]

    # Transform data into standardized project
    wgs84crs = 'EPSG:4326'
    ptCoordTransformerINWGS84 = pyproj.Transformer.from_crs(crs_from=points_crs.code,
                                                        crs_to=wgs84crs,
                                                        always_xy=True)
    xCenterWGS84, yCenterWGS84 = ptCoordTransformerINWGS84.transform(centerX, centerY)

    utmList = pyproj.database.query_utm_crs_info(datum_name='WGS 84',
                                    area_of_interest=pyproj.aoi.AreaOfInterest(
                                                        west_lon_degree=xCenterWGS84,
                                                        south_lat_degree=yCenterWGS84,
                                                        east_lon_degree=xCenterWGS84,
                                                        north_lat_degree=yCenterWGS84)
                                    )
    ptCoordTransformerWGSUTM = pyproj.Transformer.from_crs(crs_from=wgs84crs,
                                                        crs_to=utmList[0].code,
                                                        always_xy=True)
    xCenterUTM, yCenterUTM = ptCoordTransformerWGSUTM.transform(xCenterWGS84, yCenterWGS84)

    # Get spatial information about profile
    xI = df.columns.get_loc(xCol)
    yI = df.columns.get_loc(yCol)

    xStride = df.iloc[-1, xI] - df.iloc[0, xI]
    yStride = df.iloc[-1, yI] - df.iloc[0, yI]

    # Calculate all the geometry
    profileHeadingRad = np.arctan(yStride/xStride) * -1
    profileHeadingDeg = np.rad2deg(profileHeadingRad)
    cameraHeading = profileHeadingDeg + 90

    xDistHalf = xDist/2
    θ = np.deg2rad(viewAngle)
    nearDist = xDistHalf / np.tan(θ)

    bottomFOVRad = np.arctan(viewHeight/nearDist)
    bottomFOVDeg = np.rad2deg(bottomFOVRad)
    bottomFOVDeg = round(bottomFOVDeg * -1, 2)

    backCameraAngle = 180 + cameraHeading
    bcaRad = np.deg2rad(backCameraAngle)

    xCameraDist = nearDist * np.cos(bcaRad)
    xCameraLocUTM = xCenterUTM - xCameraDist

    yCameraDist = -1 * nearDist * np.sin(bcaRad)
    yCameraLocUTM = yCenterUTM - yCameraDist

    ptCoordTransformerUTMWGS = pyproj.Transformer.from_crs(crs_from=f"EPSG:{utmList[0].code}",
                                                           crs_to=wgs84crs,
                                                           always_xy=True)
    xCamWGS84, yCamWGS84 = ptCoordTransformerUTMWGS.transform(xCameraLocUTM, yCameraLocUTM)

    # Make kml file text from template
    imagePath = f"filename/{st.session_state.image_file.name}"
    import pathlib
    imagePath = pathlib.Path(imagePath)
    imagePathStr = imagePath.with_suffix('.png').name
    with open(kmlTemplateFile, 'r') as kmlFileObj:
        kmlFileText = kmlFileObj.read()
    kmlFileText = kmlFileText.replace("<name>Vertical Geologic Cross-Section</name>", f"<name>ERT Cross-Section: {imagePath.stem.split('_')[0]}</name>")
    kmlFileText = kmlFileText.replace("<longitude>-88.2261</longitude>", f"<longitude>{xCamWGS84}</longitude>")
    kmlFileText = kmlFileText.replace("<latitude>40.05775</latitude>", f"<latitude>{yCamWGS84}</latitude>")
    kmlFileText = kmlFileText.replace("<heading>58</heading>", f"<heading>{profileHeadingDeg}</heading>")
    kmlFileText = kmlFileText.replace("<bottomFov>-14</bottomFov>", f"<bottomFov>{bottomFOVDeg}</bottomFov>")
    kmlFileText = kmlFileText.replace("<near>400</near>", f"<near>{nearDist}</near>")
    kmlFileText = kmlFileText.replace("<coordinates>-88.22258,40.05940,50</coordinates>", f"<coordinates>{xCenterWGS84},{yCenterWGS84},50</coordinates>")
    kmlFileText = kmlFileText.replace("<href>CropsSci_resipyCropAlpha.png</href>", f"<href>{imagePathStr}</href>")

    st.session_state.kml_file_text = kmlFileText
    outPath = imagePath.with_suffix('.kml').name
    #with open(outPath.as_posix(), 'w') as outKML:
    #    outKML.write(kmlFileText)
    infoText = 'Copy and paste the text below into a text file with .kml extension.'
    infoText+=  '\n\nThis kml file must be saved in the same directory as your image file'
    infoText+=  '\n\nYou can also download the file using the button below'
    st.info(infoText)
    st.download_button(label='Download KML file',
                       type='primary',
                       data=kmlFileText,
                       file_name=outPath,
                       mime='application/vnd.google-earth.kml+xml')
    st.code(kmlFileText)


def show_image():
    try:
        st.image(st.session_state.image_file)
    except:
        pass

if __name__ == "__main__":
    main()
