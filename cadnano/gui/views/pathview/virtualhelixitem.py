from math import floor
from itertools import product

from PyQt5.QtCore import QRectF, QLineF, Qt, QObject, QPointF, pyqtSignal
from PyQt5.QtCore import QPropertyAnimation, pyqtProperty
from PyQt5.QtGui import QBrush, QPen, QColor, QPainterPath
from PyQt5.QtGui import QPolygonF, QTransform
from PyQt5.QtGui import QFontMetrics
from PyQt5.QtWidgets import QGraphicsItem, QGraphicsPathItem, QGraphicsRectItem
from PyQt5.QtWidgets import QGraphicsEllipseItem
from PyQt5.QtWidgets import QGraphicsSimpleTextItem

from cadnano import util
from cadnano.enum import StrandType
from cadnano.gui.controllers.itemcontrollers.virtualhelixitemcontroller import VirtualHelixItemController
from cadnano.gui.palette import getColorObj
from cadnano.gui.palette import newPenObj, getNoPen, getPenObj
from cadnano.gui.palette import getBrushObj, getNoBrush
from cadnano.gui.views.abstractitems.abstractvirtualhelixitem import AbstractVirtualHelixItem
from .strand.stranditem import StrandItem
from .virtualhelixhandleitem import VirtualHelixHandleItem
from . import pathstyles as styles


_BASE_WIDTH = styles.PATH_BASE_WIDTH
_BASE_RECT = QRectF(0,0,_BASE_WIDTH,_BASE_WIDTH)
_VH_XOFFSET = styles.VH_XOFFSET

PHOS_ITEM_WIDTH = 0.25*_BASE_WIDTH
TRIANGLE = QPolygonF()
TRIANGLE.append(QPointF(0, 0))
TRIANGLE.append(QPointF(0.75 * PHOS_ITEM_WIDTH, 0.5 * PHOS_ITEM_WIDTH))
TRIANGLE.append(QPointF(0, PHOS_ITEM_WIDTH))
TRIANGLE.append(QPointF(0, 0))
TRIANGLE.translate(0, -0.5*PHOS_ITEM_WIDTH)
T180 = QTransform()
T180.rotate(-180)
FWDPHOS_PP, REVPHOS_PP = QPainterPath(), QPainterPath()
FWDPHOS_PP.addPolygon(TRIANGLE)
REVPHOS_PP.addPolygon(T180.map(TRIANGLE))


class PropertyWrapperObject(QObject):
    def __init__(self, item):
        super(PropertyWrapperObject, self).__init__()
        self._item = item
        self._animations = {}

    def __get_brushAlpha(self):
        return self._item.brush().color().alpha()
 
    def __set_brushAlpha(self, alpha):
        brush = QBrush(self._item.brush())
        color = QColor(brush.color())
        color.setAlpha(alpha)
        self._item.setBrush(QBrush(color))

    def __get_rotation(self):
        return self._item.rotation()

    def __set_rotation(self, angle):
        self._item.setRotation(angle)

    def saveRef(self, property_name, animation):
        self._animations[property_name] = animation

    brush_alpha = pyqtProperty(int, __get_brushAlpha, __set_brushAlpha)
    rotation = pyqtProperty(float, __get_rotation, __set_rotation)
# end class


class Triangle(QGraphicsPathItem):
    def __init__(self, painter_path, parent=None):
        super(QGraphicsPathItem, self).__init__(painter_path, parent)
        self.adapter = PropertyWrapperObject(self)
    # end def
# end class


class ActivePhosItem(QGraphicsPathItem):
    def __init__(self, parent=None):
        super(QGraphicsPathItem, self).__init__(parent)
        self._part = parent.part()
        self.adapter = PropertyWrapperObject(self)
        self.setPen(getNoPen())
        self.hide()
    # end def

    def getPath(self):
        path = QPainterPath()
        _step = self._part.stepSize()
        # max_idx = self._part.maxBaseIdx()
        # for i in range(0, self._part.maxBaseIdx()+1, _step):
        #     rect = QRectF(_BASE_RECT)
        #     rect.translate(_BASE_WIDTH*i, 0)
        rect = QRectF(_BASE_RECT)
        path.addRect(rect)
        return path
    # end def

    def resize(self):
        self.setPath(self.getPath())

    def update(self, is_fwd, step_idx, color):
        if self.path().isEmpty():
            self.setPath(self.getPath())
        self.setBrush(getBrushObj(color, alpha=128))
        x = _BASE_WIDTH*step_idx
        y = -_BASE_WIDTH if is_fwd else _BASE_WIDTH*2
        self.setPos(x,y)
        self.show()
    # end def
# end class


class PreXoverLabel(QGraphicsSimpleTextItem):
    _XO_FONT = styles.XOVER_LABEL_FONT
    _FM = QFontMetrics(_XO_FONT)

    def __init__(self, idx, is_fwd, color, parent=None):
        super(QGraphicsSimpleTextItem, self).__init__(parent)
        self._num = idx
        self._is_fwd = is_fwd
        self._color = color
        self._parent = parent
        self.setFont(self._XO_FONT)
        # self.setNumberAndPos(idx)
        self.setBrush(getBrushObj('#666666'))
    # end def

    def setNumberAndPos(self, num):
        self._num = num
        str_num = str(num)
        tBR = self._FM.tightBoundingRect(str_num)
        half_label_H = tBR.height()/2.0
        half_label_W = tBR.width()/2.0

        labelX = _BASE_WIDTH/2.0 - half_label_W #
        if num == 1:  # adjust for the number one
            labelX -= half_label_W/2.0

        if self._is_fwd:
            labelY = half_label_H
        else:
            labelY = 2*half_label_H

        self.setPos(labelX, labelY)
        self.setText(str_num)
    # end def
# end class


class PreXoverItem(QGraphicsRectItem):
    def __init__(self, step, step_idx, color, is_fwd=True, parent=None):
        super(QGraphicsRectItem, self).__init__(_BASE_RECT, parent)
        self._step = step
        self._step_idx = step_idx
        self._color = color
        self._is_fwd = is_fwd
        self._parent = parent
        self._animations = []
        self.adapter = PropertyWrapperObject(self)
        self._bond_item = QGraphicsPathItem(self)
        self._bond_item.hide()
        self._label = PreXoverLabel(step_idx, is_fwd, color, self)
        self._label.hide()

        self.setPen(getNoPen())
        self.setAcceptHoverEvents(True)

        _half_bw, _bw = 0.5*_BASE_WIDTH, _BASE_WIDTH
        _half_iw, _iw = 0.5*PHOS_ITEM_WIDTH, PHOS_ITEM_WIDTH

        if is_fwd:
            phos = Triangle(FWDPHOS_PP, self)
            phos.setTransformOriginPoint(0, phos.boundingRect().center().y())
            phos.setPos(_half_bw, _bw)
            phos.setPen(getNoPen())
            phos.setBrush(getBrushObj(color))
            self._bond_item.setPen(getPenObj(color, 1))
        else:
            phos = Triangle(REVPHOS_PP, self)
            phos.setTransformOriginPoint(0, phos.boundingRect().center().y())
            phos.setPos(_half_bw, 0)
            phos.setPen(getPenObj(color, 0.5))
            phos.setBrush(getNoBrush())
            self._bond_item.setPen(getPenObj(color, 1, penstyle=Qt.DashLine, capstyle=Qt.RoundCap))
        self._phos_item = phos
    # end def

    def __repr__(self):
        cls_name = self.__class__.__name__
        vh_name = self._parent._vh_name()
        fwd_str = 'fwd' if self._is_fwd else 'rev'
        idx = self._step_idx
        angle = self.facing_angle()
        return "<%s>(%s.%s[%d].%d)" % (cls_name, vh_name, fwd_str, idx, angle)
    # end def

    ### ACCESSORS ###
    def color(self):
        return self._color

    def facing_angle(self):
        _twist = float(self._parent._vh_twist_per_base())
        if self._is_fwd:
            angle = round(((self._step_idx+(self._parent._vh_Z() / _BASE_WIDTH))*_twist)%360, 3)
        else:
            _groove = self._parent.part().minorGrooveAngle()
            angle = round(((self._step_idx+(self._parent._vh_Z() / _BASE_WIDTH))*_twist+_groove)%360, 3)
        return (self._parent._vh_angle() + angle) % 360

    def is_fwd(self):
        return self._is_fwd

    def virtualHelix(self):
        return self._parent._vh()

    def name(self):
        vh_name = self._parent._vh_name()
        fwd_str = 'fwd' if self._is_fwd else 'rev'
        idx = self.base_idx()
        angle = self.facing_angle()
        return '%s.%s.%d.%d' % (vh_name, fwd_str, idx, angle)

    def absolute_idx(self):
        return self.base_idx() + (self._parent._vh_Z() / _BASE_WIDTH)

    def base_idx(self):
        return self._step+self._step_idx

    def step_idx(self):
        return self._step_idx

    def window(self):
        return self._parent.window()

    ### EVENT HANDLERS ###
    def hoverEnterEvent(self, event):
        self._parent.updateModelActivePhos(self)
        self.setActive(True)
    # end def

    def hoverLeaveEvent(self, event):
        self._parent.updateModelActivePhos(None)
        self.setActive(False)
    # end def

    ### PUBLIC SUPPORT METHODS ###
    def hasNeighbor(self):
        pass

    def setActive(self, is_active):
        if is_active:
            self.setBrush(getBrushObj(self._color, alpha=128))
            self.animate(self, 'brush_alpha', 1, 0, 128) # overwrite running anim
            self.animate(self._phos_item, 'rotation', 500, 0, -90)
        else:
            self.setBrush(getBrushObj(self._color, alpha=0))
            self.animate(self, 'brush_alpha', 1000, 128, 0)
            self.animate(self._phos_item, 'rotation', 500, -90, 0)
    # end def

    def setActiveNeighbor(self, is_active, shortcut=None, active_item=None):
        if is_active:
            p1 = self._phos_item.scenePos()
            p2 = active_pos = active_item._phos_item.scenePos()
            scale = 3
            delta1 = -_BASE_WIDTH*scale if self._is_fwd else _BASE_WIDTH*scale
            delta2 = _BASE_WIDTH*scale if active_item.is_fwd() else -_BASE_WIDTH*scale
            c1 = self.mapFromScene(QPointF(p1.x(), p1.y()+delta1))
            c2 = self.mapFromScene(QPointF(p2.x(), p2.y()-delta2))
            pp = QPainterPath()
            pp.moveTo(self._phos_item.pos())
            pp.cubicTo(c1, c2, self._bond_item.mapFromScene(p2))
            self._bond_item.setPath(pp)
            self._bond_item.show()

            alpha = 32
            if self._is_fwd != active_item.is_fwd():
                if self.absolute_idx() == active_item.absolute_idx():
                    alpha = 255
            elif self.absolute_idx() == active_item.absolute_idx()+1:
                alpha = 255
            elif self.absolute_idx() == active_item.absolute_idx()-1:
                alpha = 255

            self.setBrush(getBrushObj(self._color, alpha=alpha))
            self.animate(self, 'brush_alpha', 500, 0, alpha)
            self.animate(self._phos_item, 'rotation', 500, 0, -90)
            self.setLabel(shortcut)

        else:
            self.setBrush(getBrushObj(self._color, alpha=0))
            self.animate(self, 'brush_alpha', 1000, 128, 0)
            self.animate(self._phos_item, 'rotation', 500, -90, 0)
            self._bond_item.hide()
            self.setLabel()
    # end def

    def setLabel(self, shortcut=None):
        if shortcut:
            self._label.show()
            self._label.setNumberAndPos(shortcut)
        else:
            self._label.hide()

    def animate(self, item, property_name, duration, start_value, end_value):
        b_name = property_name.encode('ascii')
        anim = QPropertyAnimation(item.adapter, b_name)
        anim.setDuration(duration)
        anim.setStartValue(start_value)
        anim.setEndValue(end_value)
        anim.start()
        item.adapter.saveRef(property_name, anim)
    # end def
# end class


class PreXoverItemGroup(QGraphicsRectItem):
    HUE_FACTOR = 1.6

    def __init__(self, parent=None):
        super(QGraphicsRectItem, self).__init__(parent)
        self._parent = parent
        self.setPen(getNoPen())
        part = parent.part()
        self._max_base = part.maxBaseIdx()
        step_size = part.stepSize()
        _hue_scale = step_size*self.HUE_FACTOR
        self._colors = [QColor.fromHsvF(i/_hue_scale, 0.75, 0.8).name() \
                                    for i in range(step_size)]
        self._fwd_pxo_items = {}
        self._rev_pxo_items = {}
        self._active_items = []
        self._add_pxitems(0, self._max_base+1, step_size)
    # end def

    ### ACCESSORS ###
    def window(self):
        return self._parent.window()

    ### EVENT HANDLERS ###

    ### PRIVATE SUPPORT METHODS ###
    def _add_pxitems(self, start_idx, end_idx, step_size):
        iw, half_iw = PHOS_ITEM_WIDTH, 0.5*PHOS_ITEM_WIDTH
        bw, half_bw, bw2 = _BASE_WIDTH, 0.5*_BASE_WIDTH, 2*_BASE_WIDTH
        for i in range(start_idx, end_idx, step_size):
            for j in range(step_size):
                fwd = PreXoverItem(i, j, self._colors[j], is_fwd=True, parent=self)
                rev = PreXoverItem(i, j, self._colors[-1-j], is_fwd=False, parent=self)
                fwd.setPos((i+j)*bw,-bw)
                rev.setPos((i+j)*bw,bw2)
                self._fwd_pxo_items[i+j] = fwd
                self._rev_pxo_items[i+j] = rev
            # end for
        # end for
        canvas_size = self._parent.part().maxBaseIdx()+1
        self.setRect(0, 0, bw*canvas_size, bw2)
    # end def

    def _rm_pxitems_after(self, new_max):
        for i in range(new_max+1, self._max_base+1):
            self.scene().removeItem(self._fwd_pxo_items.pop(i))
            self.scene().removeItem(self._rev_pxo_items.pop(i))
    # end def

    def part(self):
        return self._parent.part()

    def _vh_name(self):
        return self._parent.virtualHelix().getName()

    def _vh_angle(self):
        return self._parent.virtualHelix().getProperty('eulerZ')

    def _vh_twist_per_base(self):
        return self._parent.virtualHelix().getProperty('_twist_per_base')

    def _vh_Z(self):
        return self._parent.virtualHelix().getProperty('z')

    ### PUBLIC SUPPORT METHODS ###
    def getItem(self, is_fwd, idx):
        if is_fwd:
            return self._fwd_pxo_items[idx]
        else:
            return self._rev_pxo_items[idx]
    # end def

    def resize(self):
        part = self._parent.part()
        old_max = self._parent._max_base
        new_max = part.maxBaseIdx()
        if new_max == old_max:
            return
        elif new_max > old_max:
            self._add_pxitems(old_max+1, new_max, part.stepSize())
        else:
            self._rm_pxitems_after(new_max)
        self._max_base = new_max
    # end def

    def setActiveNeighbors(self, active_item, fwd_rev_idxs):
        # active_item is a PreXoverItem
        if active_item:
            # local_offset = self._vh_Z()/_BASE_WIDTH
            active_absolute_idx = active_item.absolute_idx()
            part = self._parent.part()
            cutoff = part.stepSize()/2
            active_idx = active_item.base_idx()
            step_idxs = range(0, part.maxBaseIdx(), part.stepSize())
            fwd_idxs, rev_idxs = fwd_rev_idxs
            k = 0
            pre_xovers = {}
            for i,j in product(fwd_idxs, step_idxs):
                item = self._fwd_pxo_items[i+j]
                delta = item.absolute_idx()-active_absolute_idx
                if abs(delta)<cutoff:
                    item.setActiveNeighbor(True, shortcut=str(k), active_item=active_item)
                    pre_xovers[k] = item.name()
                    k+=1
                    self._active_items.append(item)
            for i,j in product(rev_idxs, step_idxs):
                item = self._rev_pxo_items[i+j]
                delta = item.absolute_idx()-active_absolute_idx
                if abs(delta)<cutoff:
                    item.setActiveNeighbor(True, shortcut=str(k), active_item=active_item)
                    pre_xovers[k] = item.name()
                    k+=1
                    self._active_items.append(item)
            self._parent.partItem().setKeyPressDict(pre_xovers)
        else:
            self._parent.partItem().setKeyPressDict({})
            while self._active_items:
                self._active_items.pop().setActiveNeighbor(False)
    # end def

    def updatePositionsAfterRotation(self, angle):
        bw = _BASE_WIDTH
        part = self._parent.part()
        canvas_size = part.maxBaseIdx() + 1
        step_size = part.stepSize()
        xdelta = angle/360. * bw*step_size
        for i, item in self._fwd_pxo_items.items():
            x = (bw*i + xdelta) % (bw*canvas_size)
            item.setX(x)
        for i, item in self._rev_pxo_items.items():
            x = (bw*i + xdelta) % (bw*canvas_size)
            item.setX(x)
    # end def

    def updateModelActivePhos(self, pre_xover_item):
        """Notify model of pre_xover_item hover state."""
        vh = self._parent.virtualHelix()
        if pre_xover_item is None:
            self._parent.part().setProperty('active_phos', None)
            vh.setProperty('active_phos', None)
            return
        vh_name = vh.getName()
        vh_angle = vh.getProperty('eulerZ')
        idx = pre_xover_item.absolute_idx() # (f|r).step_idx
        facing_angle = pre_xover_item.facing_angle()
        is_fwd = 'fwd' if pre_xover_item.is_fwd() else 'rev'
        value = '%s.%s.%d.%d' % (vh_name, is_fwd, idx, facing_angle)
        self._parent.part().setProperty('active_phos', value)
        vh.setProperty('active_phos', value)
    # end def

    def updateViewActivePhos(self, new_active_item=None):
        while self._active_items:
            self._active_items.pop().setActive(False)
        if new_active_item:
            new_active_item.setActive(True)
            self._active_items.append(new_active_item)
    # end def


class VirtualHelixItem(QGraphicsPathItem, AbstractVirtualHelixItem):
    """VirtualHelixItem for PathView"""
    findChild = util.findChild  # for debug

    def __init__(self, part_item, model_virtual_helix, viewroot):
        super(VirtualHelixItem, self).__init__(part_item.proxy())
        self._part_item = part_item
        self._model_virtual_helix = _mvh = model_virtual_helix
        self._viewroot = viewroot
        self._getActiveTool = part_item._getActiveTool
        self._controller = VirtualHelixItemController(self, model_virtual_helix)

        self._handle = VirtualHelixHandleItem(part_item, self, viewroot)
        self._last_strand_set = None
        self._last_idx = None
        self._scaffold_background = None
        self.setFlag(QGraphicsItem.ItemUsesExtendedStyleOption)
        self.setCacheMode(QGraphicsItem.DeviceCoordinateCache)
        self.setBrush(getNoBrush())

        view = viewroot.scene().views()[0]
        view.levelOfDetailChangedSignal.connect(self.levelOfDetailChangedSlot)
        should_show_details = view.shouldShowDetails()

        pen = newPenObj(styles.MINOR_GRID_STROKE, styles.MINOR_GRID_STROKE_WIDTH)
        pen.setCosmetic(should_show_details)
        self.setPen(pen)

        self.refreshPath()
        self.setAcceptHoverEvents(True)  # for pathtools
        self.setZValue(styles.ZPATHHELIX)

        self._max_base = self.virtualHelix().getProperty('_max_length')
        
        self._repeats = mvh.getProperty('repeats')
        self._bases_per_repeat = mvh.getProperty('bases_per_repeat')
        self._turns_per_repeat = mvh.getProperty('turns_per_repeat')
        self._prexoveritemgroup = _pxig = PreXoverItemGroup(self)
        # self._activephositem = ActivePhosItem(self)
    # end def

    ### SIGNALS ###

    ### SLOTS ###

    def levelOfDetailChangedSlot(self, boolval):
        """Not connected to the model, only the QGraphicsView"""
        pen = self.pen()
        pen.setCosmetic(boolval)
        self.setPen(pen)
    # end def

    def strandAddedSlot(self, sender, strand):
        """
        Instantiates a StrandItem upon notification that the model has a
        new Strand.  The StrandItem is responsible for creating its own
        controller for communication with the model, and for adding itself to
        its parent (which is *this* VirtualHelixItem, i.e. 'self').
        """
        StrandItem(strand, self, self._viewroot)
    # end def

    def decoratorAddedSlot(self, decorator):
        """
        Instantiates a DecoratorItem upon notification that the model has a
        new Decorator.  The Decorator is responsible for creating its own
        controller for communication with the model, and for adding itself to
        its parent (which is *this* VirtualHelixItem, i.e. 'self').
        """
        pass

    def virtualHelixNumberChangedSlot(self, virtual_helix, number):
        self._handle.setNumber()
    # end def

    def virtualHelixPropertyChangedSlot(self, virtual_helix, property_key, new_value):
        ### TRANSFORM PROPERTIES ###
        if property_key == 'z':
            z = float(new_value)
            self.setX(z)
            self._handle.setX(z-_VH_XOFFSET)
            self.part().partDimensionsChangedSignal.emit(self.part(), True)
        elif property_key == 'eulerZ':
            self._handle.rotateWithCenterOrigin(new_value)
            self._prexoveritemgroup.updatePositionsAfterRotation(new_value)
        ### GEOMETRY PROPERTIES ###
        elif property_key == 'repeats':
            print(virtual_helix, property_key, new_value)
            pass
        elif property_key == 'bases_per_repeat':
            print(virtual_helix, property_key, new_value)
            pass
        elif property_key == 'turns_per_repeat':
            print(virtual_helix, property_key, new_value)
            pass
        ### RUNTIME PROPERTIES ###
        elif property_key == 'active_phos':
            hpxig = self._handle._prexoveritemgroup
            pxig = self._prexoveritemgroup
            if new_value:
                # vh-handle
                vh_name, fwd_str, base_idx, facing_angle = new_value.split('.')
                is_fwd = 1 if fwd_str == 'fwd' else 0
                step_idx = int(base_idx) % self.part().stepSize()
                h_item = hpxig.getItem(is_fwd, step_idx)
                hpxig.updateViewActivePhos(h_item)
                # vh
                item = pxig.getItem(is_fwd, step_idx)
                pxig.updateViewActivePhos(item)
            else:
                hpxig.updateViewActivePhos(None) # vh-handle
                pxig.updateViewActivePhos(None) # vh
                # self._activephositem.hide()
        elif property_key == 'neighbor_active_angle':
            hpxig = self._handle._prexoveritemgroup
            pxig = self._prexoveritemgroup
            if new_value:
                active_value = self.part().getProperty('active_phos')
                if not active_value:
                    return
                vh_name, fwd_str, base_idx, facing_angle = active_value.split('.')
                is_fwd = True if fwd_str == 'fwd' else False
                active_idx = int(base_idx)
                vh = self._part_item.getVHItemByName(vh_name)
                active_item = vh._prexoveritemgroup.getItem(is_fwd, active_idx)
                neighbors = self._model_virtual_helix.getProperty('neighbors').split()
                for n in neighbors:
                    n_name, n_angle = n.split(':')
                    if n_name == vh_name:
                        fwd_items, rev_items = hpxig.getItemsFacingNearAngle(int(n_angle))
                        fwd_idxs = [item.step_idx() for item in fwd_items]
                        rev_idxs = [item.step_idx() for item in rev_items]
                        self._prexoveritemgroup.setActiveNeighbors(active_item, (fwd_idxs, rev_idxs))
            else:
                hpxig.resetAllItemsAppearance()
                self._prexoveritemgroup.setActiveNeighbors(None, None)
    # end def

    def partPropertyChangedSlot(self, model_part, property_key, new_value):
        if property_key == 'color':
            self._handle.refreshColor()
    # end def

    def virtualHelixRemovedSlot(self, virtual_helix):
        self._controller.disconnectSignals()
        self._controller = None

        scene = self.scene()
        self._handle.remove()
        scene.removeItem(self)
        self._part_item.removeVirtualHelixItem(self)
        self._part_item = None
        self._model_virtual_helix = None
        self._getActiveTool = None
        self._handle = None
    # end def

    ### ACCESSORS ###
    def coord(self):
        return self._model_virtual_helix.coord()
    # end def

    def viewroot(self):
        return self._viewroot
    # end def

    def handle(self):
        return self._handle
    # end def

    def part(self):
        return self._part_item.part()
    # end def

    def partItem(self):
        return self._part_item
    # end def

    def number(self):
        return self._model_virtual_helix.number()
    # end def

    def virtualHelix(self):
        return self._model_virtual_helix
    # end def

    def window(self):
        return self._part_item.window()
    # end def

    ### DRAWING METHODS ###
    def isStrandOnTop(self, strand):
        return strand.strandSet().isScaffold()
        # sS = strand.strandSet()
        # isEvenParity = self._model_virtual_helix.isEvenParity()
        # return isEvenParity and sS.isScaffold() or\
        #        not isEvenParity and sS.isStaple()
    # end def

    def isStrandTypeOnTop(self, strand_type):
        return strand_type is StrandType.SCAFFOLD
        # isEvenParity = self._model_virtual_helix.isEvenParity()
        # return isEvenParity and strand_type is StrandType.SCAFFOLD or \
        #        not isEvenParity and strand_type is StrandType.STAPLE
    # end def

    def upperLeftCornerOfBase(self, idx, strand):
        x = idx * _BASE_WIDTH
        y = 0 if self.isStrandOnTop(strand) else _BASE_WIDTH
        return x, y
    # end def

    def upperLeftCornerOfBaseType(self, idx, strand_type):
        x = idx * _BASE_WIDTH
        y = 0 if self.isStrandTypeOnTop(strand_type) else _BASE_WIDTH
        return x, y
    # end def

    # http://stackoverflow.com/questions/6800193/
    def factors(n):
        return set(x for tup in ([i, n//i] 
                    for i in range(1, int(n**0.5)+1) if n % i == 0) for x in tup)

    def refreshPath(self):
        """
        Returns a QPainterPath object for the minor grid lines.
        The path also includes a border outline and a midline for
        dividing scaffold and staple bases.
        """
        bw = _BASE_WIDTH
        bw2 = 2 * bw
        part = self.part()
        path = QPainterPath()

        # sub_step_size = part.subStepSize()
        # just use second largest factor here
        factor_list = sorted(factors(self._bases_per_repeat))
        sub_step_size = factor_list[-2] if len(factor_list) > 2 else self._bases_per_repeat

        canvas_size = part.maxBaseIdx() + 1
        # border
        path.addRect(0, 0, bw * canvas_size, 2 * bw)
        # minor tick marks
        for i in range(canvas_size):
            x = round(bw * i) #+ .5
            if i % sub_step_size == 0:
                path.moveTo(x - .5,  0)
                path.lineTo(x - .5,  bw2)
                path.lineTo(x - .25, bw2)
                path.lineTo(x - .25, 0)
                path.lineTo(x,       0)
                path.lineTo(x,       bw2)
                path.lineTo(x + .25, bw2)
                path.lineTo(x + .25, 0)
                path.lineTo(x + .5,  0)
                path.lineTo(x + .5,  bw2)

            else:
                path.moveTo(x, 0)
                path.lineTo(x, 2 * bw)

        # staple-scaffold divider
        path.moveTo(0, bw)
        path.lineTo(bw * canvas_size, bw)

        self.setPath(path)

        if self._model_virtual_helix.scaffoldIsOnTop():
            scaffoldY = 0
        else:
            scaffoldY = bw
    # end def

    def resize(self):
        """Called by part on resize."""
        self.refreshPath()
        self._prexoveritemgroup.resize()
        # self._activephositem.resize()
        self._max_base = self.part().maxBaseIdx()

    ### PUBLIC SUPPORT METHODS ###
    def setActive(self, idx):
        """Makes active the virtual helix associated with this item."""
        self.part().setActiveVirtualHelix(self._model_virtual_helix, idx)
    # end def

    ### EVENT HANDLERS ###
    def mousePressEvent(self, event):
        """
        Parses a mousePressEvent to extract strand_set and base index,
        forwarding them to approproate tool method as necessary.
        """
        self.scene().views()[0].addToPressList(self)
        strand_set, idx = self.baseAtPoint(event.pos())
        self.setActive(idx)
        tool_method_name = self._getActiveTool().methodPrefix() + "MousePress"

        ### uncomment for debugging modifier selection
        # strand_set, idx = self.baseAtPoint(event.pos())
        # row, col = strand_set.virtualHelix().coord()
        # self._part_item.part().selectPreDecorator([(row,col,idx)])

        if hasattr(self, tool_method_name):
            self._last_strand_set, self._last_idx = strand_set, idx
            getattr(self, tool_method_name)(strand_set, idx)
        else:
            event.setAccepted(False)
    # end def

    def mouseMoveEvent(self, event):
        """
        Parses a mouseMoveEvent to extract strand_set and base index,
        forwarding them to approproate tool method as necessary.
        """
        tool_method_name = self._getActiveTool().methodPrefix() + "MouseMove"
        if hasattr(self, tool_method_name):
            strand_set, idx = self.baseAtPoint(event.pos())
            if self._last_strand_set != strand_set or self._last_idx != idx:
                self._last_strand_set, self._last_idx = strand_set, idx
                getattr(self, tool_method_name)(strand_set, idx)
        else:
            event.setAccepted(False)
    # end def

    def customMouseRelease(self, event):
        """
        Parses a mouseReleaseEvent to extract strand_set and base index,
        forwarding them to approproate tool method as necessary.
        """
        tool_method_name = self._getActiveTool().methodPrefix() + "MouseRelease"
        if hasattr(self, tool_method_name):
            getattr(self, tool_method_name)(self._last_strand_set, self._last_idx)
        else:
            event.setAccepted(False)
    # end def

    ### COORDINATE UTILITIES ###
    def baseAtPoint(self, pos):
        """
        Returns the (strand_type, index) under the location x,y or None.

        It shouldn't be possible to click outside a pathhelix and still call
        this function. However, this sometimes happens if you click exactly
        on the top or bottom edge, resulting in a negative y value.
        """
        x, y = pos.x(), pos.y()
        mVH = self._model_virtual_helix
        base_idx = int(floor(x / _BASE_WIDTH))
        min_base, max_base = 0, mVH.part().maxBaseIdx()
        if base_idx < min_base or base_idx >= max_base:
            base_idx = util.clamp(base_idx, min_base, max_base)
        if y < 0:
            y = 0  # HACK: zero out y due to erroneous click
        strandIdx = floor(y * 1. / _BASE_WIDTH)
        if strandIdx < 0 or strandIdx > 1:
            strandIdx = int(util.clamp(strandIdx, 0, 1))
        strand_set = mVH.getStrandSetByIdx(strandIdx)
        return (strand_set, base_idx)
    # end def

    def keyPanDeltaX(self):
        """How far a single press of the left or right arrow key should move
        the scene (in scene space)"""
        dx = self._part_item.part().stepSize() * _BASE_WIDTH
        return self.mapToScene(QRectF(0, 0, dx, 1)).boundingRect().width()
    # end def

    def hoverLeaveEvent(self, event):
        self._part_item.updateStatusBar("")
    # end def

    def hoverMoveEvent(self, event):
        """
        Parses a mouseMoveEvent to extract strand_set and base index,
        forwarding them to approproate tool method as necessary.
        """
        base_idx = int(floor(event.pos().x() / _BASE_WIDTH))
        loc = "%d[%d]" % (self.number(), base_idx)
        self._part_item.updateStatusBar(loc)

        active_tool = self._getActiveTool()
        tool_method_name = self._getActiveTool().methodPrefix() + "HoverMove"
        if hasattr(self, tool_method_name):
            strand_type, idx_x, idx_y = active_tool.baseAtPoint(self, event.pos())
            getattr(self, tool_method_name)(strand_type, idx_x, idx_y)
    # end def

    ### TOOL METHODS ###
    def pencilToolMousePress(self, strand_set, idx):
        """strand.getDragBounds"""
        # print "%s: %s[%s]" % (util.methodName(), strand_set, idx)
        active_tool = self._getActiveTool()
        if not active_tool.isDrawingStrand():
            active_tool.initStrandItemFromVHI(self, strand_set, idx)
            active_tool.setIsDrawingStrand(True)
    # end def

    def pencilToolMouseMove(self, strand_set, idx):
        """strand.getDragBounds"""
        # print "%s: %s[%s]" % (util.methodName(), strand_set, idx)
        active_tool = self._getActiveTool()
        if active_tool.isDrawingStrand():
            active_tool.updateStrandItemFromVHI(self, strand_set, idx)
    # end def

    def pencilToolMouseRelease(self, strand_set, idx):
        """strand.getDragBounds"""
        # print "%s: %s[%s]" % (util.methodName(), strand_set, idx)
        active_tool = self._getActiveTool()
        if active_tool.isDrawingStrand():
            active_tool.setIsDrawingStrand(False)
            active_tool.attemptToCreateStrand(self, strand_set, idx)
    # end def

    def pencilToolHoverMove(self, strand_type, idx_x, idx_y):
        """Pencil the strand is possible."""
        part_item = self.partItem()
        active_tool = self._getActiveTool()
        if not active_tool.isFloatingXoverBegin():
            temp_xover = active_tool.floatingXover()
            temp_xover.updateFloatingFromVHI(self, strand_type, idx_x, idx_y)
    # end def
