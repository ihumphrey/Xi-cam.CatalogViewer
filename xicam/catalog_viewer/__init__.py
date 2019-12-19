from qtpy.QtWidgets import QLabel
from xicam.plugins import GUIPlugin, GUILayout
from xicam.gui.widgets.dynimageview import DynImageView
from xicam.gui.widgets.imageviewmixins import XArrayView, CatalogView
from xicam.core.data import MetaXArray

from qtpy.QtWidgets import QToolBar, QComboBox
from qtpy.QtCore import QItemSelectionModel, Signal, Qt
from qtpy.QtGui import QStandardItem, QStandardItemModel
from xicam.gui.widgets.tabview import TabView
from xicam.core.data import NonDBHeader


class FieldSelector(QToolBar):
    sigFieldChanged = Signal(str)

    def __init__(self, model: QStandardItemModel, selectionmodel: QItemSelectionModel, *args, **kwargs):
        super(FieldSelector, self).__init__(*args)

        self.headermodel = model
        self.selectionmodel = selectionmodel
        self.headermodel.dataChanged.connect(self.updateFieldComboBox)

        self.addWidget(QLabel("Field: "))
        self.detectorcombobox = QComboBox()
        self.detectorcombobox.setSizeAdjustPolicy(QComboBox.AdjustToContents)
        self.addWidget(self.detectorcombobox)
        self.addSeparator()
        self.detectorcombobox.currentTextChanged.connect(self.sigFieldChanged)

    def updateFieldComboBox(self, start, end):
        print('updateFieldComboBox')
        originalField = self.detectorcombobox.currentText()
        if self.headermodel.rowCount():
            # TODO-- remove hard-coding of stream
            stream = "primary"
            data = self.headermodel.item(start.row()).data(Qt.UserRole)
            if type(data) is NonDBHeader:
                fields = ['sample_name']
            else:
                print('getting catalog')
                catalog = getattr(data, stream)
                print('getting fields')
                allFields = catalog.metadata['descriptors'][0]['data_keys']
                fields = []
                print('getting image fields')
                for field, descriptorDict in allFields.items():
                    if len(descriptorDict['shape']) >= 2:
                        fields.append(field)
            # fields = [ technique["data_mapping"]["data_image"][1] for technique in catalog.metadata["techniques"] if technique["technique"] == "scattering" ]
            self.detectorcombobox.clear()
            print('adding to combo')
            self.detectorcombobox.addItems(fields)
            # fieldIndex = 0
            # if "technique" in data.metadata:
            #     field = data.metadata["techniques"]
            #     fieldIndex = self.detectorcombobox.findText(field)
            # else:
            #     print(self.detectorcombobox.currentIndex())
            #     print(originalField)
            #     if self.detectorcombobox.currentIndex() == -1:
            #         self.detectorcombobox.setCurrentIndex(0)
            #     else:
            #         self.detectorcombobox.setCurrentIndex(self.detectorcombobox.findText(originalField))



class CatalogViewerBlend(XArrayView, CatalogView):
    pass


class CatalogViewerPlugin(GUIPlugin):
    name = 'Catalog Viewer'

    def __init__(self):
        self._model = QStandardItemModel()
        self._selectionModel = QItemSelectionModel(self._model)
        self._toolBar = FieldSelector(model=self._model, selectionmodel=self._selectionModel)
        self._tabView = TabView(catalogmodel=self._model,
                                selectionmodel=self._selectionModel,
                                widgetcls=CatalogViewerBlend,
                                stream='primary',
                                field=None, # if field is None or '', the setCatalog will fail its all() check
                                bindings=[(self._toolBar.sigFieldChanged, 'fieldChanged')])
        self.stages = {'Viewer': GUILayout(self._tabView, top=self._toolBar), }
        super(CatalogViewerPlugin, self).__init__()

    def appendCatalog(self, runcatalog, **kwargs):
        fields = getattr(runcatalog, self._tabView.stream).metadata['descriptors'][0]['data_keys']
        greedyFieldDefault = None
        for field, descriptorDict in fields.items():
            if len(descriptorDict['shape']) >= 2:
                greedyFieldDefault = field
                break
        if greedyFieldDefault:
            self._tabView.field = greedyFieldDefault
        print(f'greedyFieldDefault: {greedyFieldDefault}')
        catalogItem = QStandardItem()
        catalogItem.setData("test", Qt.DisplayRole)
        catalogItem.setData(runcatalog, Qt.UserRole)
        self._model.appendRow(catalogItem)
        self._model.dataChanged.emit(catalogItem.index(), catalogItem.index())
        # xdata = runcatalog().primary.to_dask()['fccd_image'].data[0, :, :,
        #        :]  # The test data is 4-dimensional; ignoring last dim
        # self.imageview.setImage(MetaXArray(xdata))

    def appendHeader(self, header):
        self.appendCatalog(header)


# find fields that have image data (size >= 2)
# if techniques is defined, use that to get the default data_image
# otherwise; pick the first field (if index is -1)