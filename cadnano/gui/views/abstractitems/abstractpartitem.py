class AbstractPartItem(object):
    """
    AbstractPartItem is a base class for partitems in all views.
    It includes slots that get connected in PartItemController which
    can be overridden.

    If you want to add a new signal to the model, adding the slot here
    means it's not necessary to add the same slot to every item across
    all views.
    """

    def __init__(self):
        self._oligo_item_hash = {}
        self._virtual_helix_item_hash = {}
    # end def

    def part(self):
        return self._model_part

    def setPart(self, new_part):
        self._model_part = new_part
    # end def

    def document(self):
        """Return a reference to the model's document object"""
        return self._model_part.document()
    # end def

    def scaleFactor(self):
        return self.scale_factor
    # end def

    def idToVirtualHelixItem(self, id_num):
        return self._virtual_helix_item_hash[id_num]
    # end def

    def partDimensionsChangedSlot(self, part):
        pass
    def partOligoAddedSlot(self, part, oligo):
        pass
    def partParentChangedSlot(self, sender):
        pass
    def partPropertyChangedSlot(model_part, property_key, new_value):
        pass
    def partRemovedSlot(self, sender):
        pass
    def partSelectedChangedSlot(self, model_part, is_selected):
        pass
    def partActiveVirtualHelixChangedSlot(self, sender, id_num):
        pass
    def partActiveBaseInfoSlot(self, sender, info):
        pass
    def partPreDecoratorSelectedSlot(self, sender):
        pass
    def updatePreXoverItemsSlot(self, sender):
        pass
    def partVirtualHelixAddedSlot(self, sender):
        pass
    def partVirtualHelixRemovedSlot(self, sender, id_num):
        pass
    def partVirtualHelixRenumberedSlot(self, sender, id_num):
        pass
    def partVirtualHelixResizedSlot(self, sender, id_num):
        pass
    def partVirtualHelicesReorderedSlot(self, sender):
        pass
    def partVirtualHelicesTranslatedSlot(self, sender, vh_set):
        pass
    def partVirtualHelicesSelectedSlot(self, sender, vh_set, is_adding):
        """ is_adding (bool): adding (True) virtual helices to a selection
        or removing (False)
        """
        pass
    def partVirtualHelixPropertyChangedSlot(self, sender, id_num, new_value):
        pass
# end class


