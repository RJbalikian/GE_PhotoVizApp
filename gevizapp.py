import codecs
import traceback

from PIL import Image
import numpy as np
import pandas as pd
import pyproj

import streamlit as st

CRS_LIST = pyproj.database.query_crs_info()
CRS_STR_LIST = [f"{crs.auth_name}:{crs.code} - {crs.name}" for crs in CRS_LIST]
CRS_DICT = {f"{crs.auth_name}:{crs.code} - {crs.name}": crs for crs in CRS_LIST}
DEFAULT_POINTS_CRS = "EPSG:4326 - WGS 84"
DEFAULT_POINTS_CRS_INDEX = CRS_STR_LIST.index(DEFAULT_POINTS_CRS)

st.set_page_config(layout='wide')


def main():
    mainContainer = st.session_state.main_container = st.container()
    ifCond = hasattr(st.session_state, 'image_file')
    dfCond = hasattr(st.session_state, 'df')

    if ifCond:
        ifNameCond = hasattr(st.session_state.image_file, 'name')
        if ifNameCond:
            mainContainer.image(st.session_state.image_file, caption=st.session_state.image_file.name, width='stretch')
    if dfCond:
        mainContainer.dataframe(st.session_state.df)

    if not ifCond and not dfCond:
        mainContainer.title("Google Earth 3D Image Visualization Tool")
        mdText = 'This app allows for pseudo-3D visualization of cross section data using a Google Earth Photo Overlay.\n\n'
        mdText += '\n\n An image file with your data is needed as well as a delimited text file with the following columns:'
        mdText += '\n\n * Distance (the distance along the cross section)\n * X: x coordinates of your data\n * Y: y coordinates of your data'
        mdText += '\n\n You will need to select the CRS of your coordinates in the dropdown. By default, it uses decimal degrees in WGS84.\n\n'
        mdText += '### NOTE THAT PHOTO OVERLAYS ARE ONLY SUPPORTED IN THE DESKTOP EDITION OF GOOGLE EARTH!.'
        mainContainer.markdown(mdText)

    with st.sidebar:
        st.title("GE 3D Image Visualization")

        st.file_uploader('Upload Image File',
                         key='image_file',
                         on_change=show_image,
                         help='Upload an image file that contains the data to display vertically in Google Earth')

        st.text_area('Copy/paste table with location values',
                     key='table_text',
                     on_change=parse_table_text,
                     help='The easiest way to do this is to open an excel document with your csv data copy/paste that data into this box.')
        st.checkbox('Data Includes Header',
                    value=True,
                    key='includes_header',
                    help='Whether the data you pasted includes headers (recommended headers are "X" for x-coordinates, "Y" for y-coordinates, and "Distance" for distance along profile)')
        lineSepCol, itemSepCol = st.columns([0.5, 0.5])
        lineSepCol.text_input('Line Separator',
                              value=r'\n',
                              key='line_sep',
                              help='Character separating lines. This is set to the default from copy/pasting from Excel.')

        itemSepCol.text_input('Item Separator',
                              value=r'\t',
                              key='item_sep',
                              help='Character separating items within a line. This is set to the default from copy/pasting from Excel.')

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
                          help='Name of column containing X-coordinates',
                          key='x_column')
        yColCol.selectbox("Select Y Column",
                          options=yColOpts,
                          index=yColInd,
                          help='Name of column containing Y-coordinates',
                          key='y_column')
        distCol.selectbox("Select Distance Column",
                          options=distOpts,
                          index=distColInd,
                          help='Name of column containing cross sectional distance',
                          key='dist_column'
                          )
        st.selectbox('CRS of Data Coordinates',
                     options=CRS_STR_LIST,
                     index=DEFAULT_POINTS_CRS_INDEX,
                     help='CRS of X- and Y-Coordinates',
                     key='input_crs')

        st.header("Export Options", divider='rainbow')
        st.number_input("Cross Section Height [m]",
                        min_value=1,
                        max_value=10000,
                        value=100,
                        key='view_height',
                        help='The height to which the image will extend above ground level in meters')

        st.pills("Make image double-sided?",
                 options=["Single", "Double"],
                 default="Double",
                 selection_mode='single',
                 help="Photo overlays are viewed by a 'camera' in GE, so only display one sided. \
                       The image can be reversed and draped at the same location for double-sided.\
                       Double-sided outputs must be in KMZ",
                 on_change=side_change,
                 key='sidedness')

        if hasattr(st.session_state, 'export_type_default'):
            epdef = st.session_state.export_type_default
            if hasattr(st.session_state, 'export_type'):
                st.session_state.export_type = epdef
        else:
            epdef = 'KMZ'

        st.pills("Export KML or KMZ?",
                 options=["KML", "KMZ"],
                 selection_mode='single',
                 default=epdef,
                 on_change=et_change,
                 help="KML exports are smaller but require the KML file and image file to be in the same directory. KMZ packages the image file and KML together.",
                 key='export_type')
        
        st.header("", divider='rainbow')
        buttonLabel='Generate 3D KML Visualization'
        if st.session_state.export_type == 'KMZ':
            buttonLabel='Generate 3D KMZ Visualization'
        bcon = st.container(horizontal_alignment='right')
        bcon.button(buttonLabel,
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


def get_crs_info():
    import webbrowser
    crscode = st.session_state.crs_info_select.split(":")[1].split(" ")[0]
    webbrowser.open(f"https://epsg.io/?q={crscode}")


def et_change():
    st.session_state.export_type_default = st.session_state.export_type
    if st.session_state.sidedness == 'Double':
        st.session_state.export_type_default = st.session_state.export_type = "KMZ"


def side_change():
    if st.session_state.sidedness == "Double":
        if hasattr(st.session_state, 'export_type'):
            st.session_state.export_type_default='KMZ'


def generate_kml():

    # Initialize variables
    kmlTemplateFile = r"TEMPLATE_ERT_GoogleEarthBillboard.kml"
    df = st.session_state.df
    xCol = st.session_state.x_column
    yCol = st.session_state.y_column
    xDistCol = st.session_state.dist_column

    viewHeight = st.session_state.view_height
    viewAngle = 26.5

    # Get initial information
    xDist = abs(df[xDistCol].max() - df[xDistCol].min())
    centerX = round(df[xCol].mean(), 2)
    centerY = round(df[yCol].mean(), 2)
    points_crs = CRS_DICT[st.session_state.input_crs]

    # Transform data into standardized projections
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
    kmlFileText = kmlFileText.replace("<altitude>100</altitude>", f"<altitude>{viewHeight}</altitude>")
    kmlFileText = kmlFileText.replace("<heading>58</heading>", f"<heading>{profileHeadingDeg}</heading>")
    kmlFileText = kmlFileText.replace("<bottomFov>-14</bottomFov>", f"<bottomFov>{bottomFOVDeg}</bottomFov>")
    kmlFileText = kmlFileText.replace("<near>400</near>", f"<near>{nearDist}</near>")
    kmlFileText = kmlFileText.replace("<coordinates>-88.22258,40.05940,50</coordinates>", f"<coordinates>{xCenterWGS84},{yCenterWGS84},50</coordinates>")
    if st.session_state.export_type == 'KMZ':
        kmlFileText = kmlFileText.replace("<href>CropsSci_resipyCropAlpha.png</href>", f"<href>files/{imagePathStr}</href>")
    else:
        kmlFileText = kmlFileText.replace("<href>CropsSci_resipyCropAlpha.png</href>", f"<href>{imagePathStr}</href>")

    if st.session_state.sidedness == "Double":
        kmlFileText = kmlFileText.replace(' <', '  <')
        kmlHeader = kmlFileText[:129]
        kmlEnd = kmlFileText[-6:]
        kmlBody0 = kmlBody1 = kmlFileText[129:-6]

        oppAngDeg = 180 + profileHeadingDeg #profileHeadingDeg - 180
        revXDist = -1 * nearDist * np.sin(np.deg2rad(oppAngDeg))
        revYDist = -1 * nearDist * np.cos(np.deg2rad(oppAngDeg))
        revXCoordUTM = xCenterUTM + revXDist
        revYCoordUTM = yCenterUTM + revYDist
        xCamWGS84Rev, yCamWGS84Rev = ptCoordTransformerUTMWGS.transform(revXCoordUTM, revYCoordUTM)

        imagePathStrRev = imagePath.with_suffix('.png').with_stem(imagePath.stem+'_rev').name
        kmlBody1 = kmlBody1.replace(f"<longitude>{xCamWGS84}</longitude>", f"<longitude>{xCamWGS84Rev}</longitude>")
        kmlBody1 = kmlBody1.replace(f"<latitude>{yCamWGS84}</latitude>", f"<latitude>{yCamWGS84Rev}</latitude>")
        kmlBody1 = kmlBody1.replace(f"<heading>{profileHeadingDeg}</heading>", f"<heading>{oppAngDeg}</heading>")
        kmlBody1 = kmlBody1.replace(f"<href>files/{imagePathStr}</href>", f"<href>files/{imagePathStrRev}</href>")

        kmlFileText = kmlHeader + \
                      ' <Document>\n' + \
                      kmlBody0 + '\n' + kmlBody1 + \
                      ' </Document>\n' + kmlEnd

    st.session_state.kml_file_text = kmlFileText

    # Get download and visualization read y

    if st.session_state.export_type == 'KMZ':
        import io
        import zipfile
        
        buffer = io.BytesIO()


        # Convert each PIL Image to bytes via a BytesIO buffer
        def image_to_bytes(img, format="PNG"):
            buf = io.BytesIO()
            img.save(buf, format=format)
            return buf.getvalue()
        
        outPath = imagePath.with_suffix('.kmz').name

        # Open image with PIL
        img1 = Image.open(st.session_state.image_file)
        
        if st.session_state.sidedness == "Single":
            # Build KMZ in memory
            with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as kmz:
                kmz.writestr("doc.kml", kmlFileText)
                kmz.writestr(f"files/{imagePathStr}", image_to_bytes(img1))

        else:  # st.session_state.sidedness == "Double":
            revimg2 = img1.transpose(Image.FLIP_LEFT_RIGHT)

            # Build KMZ in memory
            with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as kmz:
                kmz.writestr("doc.kml", kmlFileText)
                kmz.writestr(f"files/{imagePathStr}", image_to_bytes(img1))
                kmz.writestr(f"files/{imagePathStrRev}", image_to_bytes(revimg2))

        kmz_bytes = buffer.getvalue()

        st.download_button(label=f'Download {st.session_state.export_type} file',
                           type='primary',
                           data=kmz_bytes,
                           file_name=outPath,
                           mime='application/vnd.google-earth.kmz')

    else:
        outPath = imagePath.with_suffix('.kml').name
        st.download_button(label=f'Download {st.session_state.export_type} file',
                           type='primary',
                           data=kmlFileText,
                           file_name=outPath,
                           mime='application/vnd.google-earth.kml+xml')

    infoText = 'Copy and paste the text below into a text file with .kml extension.'
    infoText += '\n\nThis kml file must be saved in the same directory as your image file'
    infoText += '\n\nYou can also download the file using the button below'

    st.header('*Output KML file must be saved in same directory as the cross section image!*')
    st.info(infoText)
    st.code(kmlFileText)


def show_image():
    try:
        st.image(st.session_state.image_file)
    except Exception:
        pass


if __name__ == "__main__":
    main()
