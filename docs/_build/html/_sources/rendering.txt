================
Canvas Rendering
================

The members of this package make plots from histograms or other wrapped
ROOT-objects. The 'Renderers' extend the functionality of wrappers for drawing.
The ROOT-canvas is build with the ``CanvasBuilder`` class.
The functionality of ``CanvasBuilder`` can be extended with decorators, see
below.


Renderers for wrapper types
===========================

.. autoclass:: cmstoolsac3b.rendering.Renderer
   :members:

.. autoclass:: cmstoolsac3b.rendering.HistoRenderer
   :members:
   :show-inheritance:

.. autoclass:: cmstoolsac3b.rendering.StackRenderer
   :members:
   :show-inheritance:


Canvas Building
===============

.. autoclass:: cmstoolsac3b.rendering.CanvasBuilder
   :members:


Decorators for CanvasBuilder
============================

Decorators are the way to add content to canvases, like a legend, boxes, lines,
text, etc.. See :ref:`decorator-module` for details on the decorator
implementation. Apply as below (e.g. with a 'Legend' and a 'TextBox'
Decorator)::

    cb = CanvasBuilder(wrappers)
    cb = Legend(cb, x1=0.2, x2=0.5)
    cb = Textbox(cb, text="Some boxed Text")
    canvas_wrp = cb.build_canvas()

.. autoclass:: cmstoolsac3b.rendering.Legend
   :members:
   :show-inheritance:

