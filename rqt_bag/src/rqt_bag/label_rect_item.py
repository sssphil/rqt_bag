from python_qt_binding.QtCore import qDebug, QPointF, QRectF, Qt, qWarning, Signal
from python_qt_binding.QtGui import QBrush, QCursor, QColor, QFont, \
    QFontMetrics, QPen, QPolygonF, QMouseEvent
from python_qt_binding.QtWidgets import QGraphicsItem, QGraphicsRectItem, QInputDialog, QMessageBox


class LabelRectItem(QGraphicsRectItem):
    class HandleItem(QGraphicsRectItem):
        def __init__(self, draw_handle, change_callback, *arg, **kwargs):
            super(LabelRectItem.HandleItem, self).__init__(*arg, **kwargs)
            # setBrush(QBrush(Qt::lightGray));
            self.setFlag(QGraphicsItem.ItemIsMovable, True)
            self.setFlag(QGraphicsItem.ItemSendsGeometryChanges, True)

            self.draw_handle = draw_handle
            self.change_callback = change_callback

        def itemChange(self, change, value):
            # value is the new position of the handle
            if change == QGraphicsItem.ItemPositionChange:
                # limit position change to x only
                pos = self.pos()
                value.setY(pos.y())
                # resize callback
                if self.change_callback:
                    self.change_callback(value)
            elif change == QGraphicsItem.ItemPositionHasChanged:
                pass
            return value

        def paint(self, painter, option, widget):
            self.draw_handle(painter, option, widget)

    # we want the drawn rect to be at around local origin and move it around with self.setPos()
    # and the self.pos().x() will be aligned with stamp for zooming update
    # the motivation behind this is that the itemChange method gives the new position instead of relative change
    def __init__(self, stamp, duration, rect, parent):
        super(LabelRectItem, self).__init__(QRectF(0, 0, rect.width(), rect.height()), parent)
        self.setPos(rect.left(), rect.top())

        self.stamp = stamp
        self.duration = duration

        self.rect_color = QColor(0, 121, 255, 191)

        self.handle_width = 10
        self.handle_pointer_size = (self.handle_width/2, self.handle_width/2)
        self.handle_color = QColor(255, 121, 0, 191)
        self.handle_padding = 5
        self._default_brush = QBrush(Qt.black, Qt.SolidPattern)
        self._default_pen = QPen(Qt.black)

        # since positions are set to the midpoint of the edges, we start from 0,0 (the midpoint)
        def draw_left_handle(painter, option, widget):
            painter.setPen(QPen(self.handle_color))
            painter.setBrush(QBrush(self.handle_color))

            pw, ph = self.handle_pointer_size

            # Left triangle
            px = -self.handle_padding
            py = 0
            painter.drawPolygon(
                QPolygonF([QPointF(px, py + ph), QPointF(px, py - ph), QPointF(px - pw, py)]))

            painter.setBrush(self._default_brush)
            painter.setPen(self._default_pen)

        def draw_right_handle(painter, option, widget):
            painter.setPen(QPen(self.handle_color))
            painter.setBrush(QBrush(self.handle_color))

            pw, ph = self.handle_pointer_size

            # Right triangle
            px = self.handle_padding
            py = 0
            painter.drawPolygon(
                QPolygonF([QPointF(px, py + ph), QPointF(px, py - ph), QPointF(px + pw, py)]))

            painter.setBrush(self._default_brush)
            painter.setPen(self._default_pen)

        def change_callback(value):
            self.update_label()

        # initialize with only handle_width, height will be updated later
        self.left_handle = LabelRectItem.HandleItem(draw_left_handle, change_callback, QRectF(-self.handle_width, -self.handle_width/2,self.handle_width,self.handle_width), parent=self)
        self.right_handle = LabelRectItem.HandleItem(draw_right_handle, change_callback, QRectF(0, -self.handle_width/2,self.handle_width,self.handle_width), parent=self)
        self.update_handle()

        self.setFlag(QGraphicsItem.ItemIsMovable, True)
        self.setFlag(QGraphicsItem.ItemSendsGeometryChanges, True)

    def get_params(self):
        return self.stamp, self.duration

    def paint(self, painter, option, widget):
        painter.setPen(QPen(self.rect_color))
        painter.setBrush(QBrush(self.rect_color))

        painter.drawRect(self.rect())

        painter.setBrush(self._default_brush)
        painter.setPen(self._default_pen)

    def itemChange(self, change, value):
        # value is the new position
        if change == QGraphicsItem.ItemPositionChange:
            # limit position change to x only
            pos = self.pos()
            value.setY(pos.y())

            self.update_label()

        elif change == QGraphicsItem.ItemPositionHasChanged:
            pass

        return value

    # update label rect using stamp and duration
    # this is useful for zooming and dragging timeline (from TimelineFrame)
    def redraw(self):
        # disables geometry change signal so itemChange will not be called
        self.setFlag(QGraphicsItem.ItemSendsGeometryChanges, False)

        # change pos.x by stamp, and rect.width by duration
        x = self.parentItem().map_stamp_to_x(self.stamp, False)
        pos = self.pos()
        self.setPos(x, pos.y())

        rect = self.rect()
        width = self.parentItem().map_dstamp_to_dx(self.duration)
        rect.setWidth(width)
        rect.setLeft(0)
        self.setRect(rect)

        # update handle
        self.update_handle()

        self.setFlag(QGraphicsItem.ItemSendsGeometryChanges, True)

    # update label rects and stamp/duration
    def update_label(self):
        left = self.left_handle.pos().x()
        width = self.right_handle.pos().x() - self.left_handle.pos().x()

        if width <= 0:
            left = self.right_handle.pos().x()
            width = -width

        rect = self.rect()
        rect.setLeft(left)
        rect.setWidth(width)
        self.setRect(rect)

        self.stamp = self.parentItem().map_x_to_stamp(left + self.pos().x(), False)
        self.duration = self.parentItem().map_dx_to_dstamp(width)

        self.update_handle()

    # reposition handles
    def update_handle(self):

        # clear flags so itemChange() method won't be triggered to restrict positions
        self.left_handle.setFlag(QGraphicsItem.ItemSendsGeometryChanges, False)
        self.right_handle.setFlag(QGraphicsItem.ItemSendsGeometryChanges, False)

        rect = self.rect()

        # positions are set to the midpoint of the rect's left/right edges
        self.left_handle.setPos(QPointF(rect.left(), rect.top() + rect.height()/2))
        self.right_handle.setPos(QPointF(rect.right(), rect.top() + rect.height()/2))

        # maintain handles' rect (using constants) at around the local origin (or the position in parent's coord)
        self.left_handle.setRect(-self.handle_width, -rect.height()/2, self.handle_width, rect.height())
        self.right_handle.setRect(0, -rect.height() / 2, self.handle_width, rect.height())

        self.left_handle.setFlag(QGraphicsItem.ItemSendsGeometryChanges, True)
        self.right_handle.setFlag(QGraphicsItem.ItemSendsGeometryChanges, True)

