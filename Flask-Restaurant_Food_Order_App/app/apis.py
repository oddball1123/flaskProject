from app import application
from flask import session
from app.models import *
from app import *
import uuid
from marshmallow import Schema, fields
from flask_restful import Resource, Api
from flask_apispec.views import MethodResource
from flask_apispec import marshal_with, doc, use_kwargs


class SignUpRequest(Schema):
    name = fields.Str(default="name")
    username = fields.Str(default="username")
    password = fields.Str(default="password")
    level = fields.Str(default="0")


class AddItemRequest(Schema):
    item_id = fields.Str(default="item_id")
    item_name = fields.Str(default="item_name")
    calories_per_gm = fields.Integer(default=100)
    available_quantity = fields.Integer(default=1)
    restaurant_name = fields.Str(default="restaurant_name")
    unit_price = fields.Integer(default=10)


class ItemSchema(Schema):
    item_id = fields.Str()
    quantity = fields.Int()


class AddItemOrderRequest(Schema):
    order_items = fields.List(fields.Nested(ItemSchema))


class GetOrdersByCustId(Schema):
    cust_id = fields.Str()


class LoginRequest(Schema):
    username = fields.Str(default="username")
    password = fields.Str(default="password")


class AddVendorRequest(Schema):
    user_id = fields.Str(default="user_id")


class PlaceOrderRequest(Schema):
    order_id = fields.Str(default="order_id")


class VendorsListResponse(Schema):
    vendors = fields.List(fields.Dict())


class OrdersListResponse(Schema):
    orders = fields.List(fields.Dict())


class ItemsListResponse(Schema):
    items = fields.List(fields.Dict())


class ListOrderResponse(Schema):
    orders = fields.List(fields.Dict())


class APIResponse(Schema):
    message = fields.Str(default="Success")


class SignUpAPI(MethodResource, Resource):
    @doc(description='Sign Up API', tags=['SignUp API'])
    @use_kwargs(SignUpRequest, location='json')
    @marshal_with(APIResponse)
    def post(self, **kwargs):
        try:
            user = User(
                uuid.uuid4(),
                kwargs['name'],
                kwargs['username'],
                kwargs['password'],
                kwargs['level']
            )
            db.session.add(user)
            db.session.commit()
            return APIResponse().dump(dict(message='User successfully registered')), 200
        except Exception as e:
            return APIResponse().dump(dict(message=f'Not able to Sign up user, Exception: {e}')), 400


api.add_resource(SignUpAPI, '/signup')
docs.register(SignUpAPI)


class LoginAPI(MethodResource, Resource):
    @doc(description='Login API', tags=['Login API'])
    @use_kwargs(LoginRequest, location='json')
    @marshal_with(APIResponse)
    def post(self, **kwargs):
        try:
            user = User.query.filter_by(username=kwargs['username'], password=kwargs['password']).first()
            if user:
                session['user_id'] = user.user_id
                return APIResponse().dump(dict(message='User successfully logged in')), 200
            else:
                return APIResponse().dump(dict(message='User not found')), 404
        except Exception as e:
            return APIResponse().dump(dict(message=f'Not able to login user : {e}')), 400


api.add_resource(LoginAPI, '/login')
docs.register(LoginAPI)


class LogoutAPI(MethodResource, Resource):
    @doc(description='Logout API', tags=['Logout API'])
    @marshal_with(APIResponse)
    def post(self, **kwargs):
        try:
            if session['user_id']:
                session['user_id'] = None
                return APIResponse().dump(dict(message='User is successfully logged out')), 200
            else:
                return APIResponse().dump(dict(message='User is not logged in')), 401
        except Exception as e:
            return APIResponse().dump(dict(message=f'Not able to logout user : {str(e)}')), 400


api.add_resource(LogoutAPI, '/logout')
docs.register(LogoutAPI)


class AddVendorAPI(MethodResource, Resource):
    @doc(description='Add Vendor API', tags=['AddVendor API'])
    @use_kwargs(AddVendorRequest, location='json')
    @marshal_with(APIResponse)
    def post(self, **kwargs):
        try:
            # check that user is logged in
            if session['user_id']:
                user = User.query.filter_by(user_id=kwargs['user_id']).first()
                if user:
                    user.level = 1
                    db.session.commit()
                    return APIResponse().dump(dict(message='User is successfully updated to vendor')), 200
                else:
                    return APIResponse().dump(dict(message='Invalid user_id')), 400
            else:
                return APIResponse().dump(dict(message='Please login before adding vendor')), 401
        except Exception as e:
            return APIResponse().dump(dict(message=f'Not able to update user to vendor, Exception: {e}')), 404


api.add_resource(AddVendorAPI, '/add_vendor')
docs.register(AddVendorAPI)


class GetVendorsAPI(MethodResource, Resource):
    @doc(description='Vendors List API', tags=['VendorsList API'])
    @marshal_with(VendorsListResponse, APIResponse)
    def get(self):
        try:
            # check that user is logged in
            if session['user_id']:
                # get all vendors data from User Table
                vendors = User.query.filter_by(level="1").all()
                vendors_list = []
                for vendor in vendors:
                    vendor_dict = {'user_id': vendor.user_id,
                                   'user_name': vendor.username,
                                   'name': vendor.name}

                    # check vendor items/restaurants from Item Table
                    items = Item.query.filter_by(vendor_id=vendor.user_id).all()
                    if items:
                        for item in items:
                            item_dict = {'item_name': item.item_name,
                                         'item_store': item.restaurant_name,
                                         'item_availability': item.available_quantity}

                            vendor_dict[item.item_id] = item_dict
                    else:
                        vendor_dict['items'] = "Vendor has no items for sale currently"
                    # add vendor data to vendors_list
                    vendors_list.append(vendor_dict)
                return VendorsListResponse().dump(dict(vendors=vendors_list)), 200
            else:
                return APIResponse().dump(dict(message='User is not logged in')), 401
        except Exception as e:
            return APIResponse().dump(dict(message='Not able to list vendors')), 400


api.add_resource(GetVendorsAPI, '/list_vendors')
docs.register(GetVendorsAPI)


class AddItemAPI(MethodResource, Resource):
    @doc(description='Add Item API', tags=['AddItem API'])
    @use_kwargs(AddItemRequest, location='json')
    @marshal_with(APIResponse)
    def post(self, **kwargs):
        try:
            # check user is logged in
            user_id = session['user_id']
            if user_id:
                # check if logged in user is a vendor
                user = User.query.filter_by(user_id=user_id, level=1).first()
                if user:
                    item = Item(
                        kwargs['item_id'],
                        user_id,
                        kwargs['item_name'],
                        kwargs['calories_per_gm'],
                        kwargs['available_quantity'],
                        kwargs['restaurant_name'],
                        kwargs['unit_price']
                    )
                    db.session.add(item)
                    db.session.commit()
                    return APIResponse().dump(dict(message='Item addd successfully')), 200
                else:
                    return APIResponse().dump(dict(message='Only Vendors can add Item')), 404
            else:
                return APIResponse().dump(dict(message='Please Login before adding Item')), 404
        except Exception as e:
            return APIResponse().dump(dict(message=f'Not able to add item, Exception: {e}')), 400


api.add_resource(AddItemAPI, '/add_item')
docs.register(AddItemAPI)


class ListItemsAPI(MethodResource, Resource):
    @doc(description='Items List API', tags=['ItemsList API'])
    @marshal_with(ItemsListResponse)
    def get(self):
        try:
            if session['user_id']:
                items = Item.query.all()
                items_list = []
                for item in items:
                    item_dict = {'item_id': item.item_id,
                                 'vendor_id': item.vendor_id,
                                 'item_name': item.item_name,
                                 'calories_per_gm': item.calories_per_gm,
                                 'available_quantity': item.available_quantity,
                                 'restaurant_name': item.restaurant_name,
                                 'unit_price': item.unit_price,
                                 'is_active': item.is_active,
                                 'created_ts': item.created_ts,
                                 'updated_ts': item.updated_ts
                                 }
                    items_list.append(item_dict)
                return ItemsListResponse().dump(dict(items=items_list)), 200
            else:
                return APIResponse().dump(dict(message='User is not Logged in')), 401
        except Exception as e:
            return APIResponse().dump(dict(message=f'Not able to list items, Exception: {e}')), 400


api.add_resource(ListItemsAPI, '/list_items')
docs.register(ListItemsAPI)


class CreateItemOrderAPI(MethodResource, Resource):
    @doc(description='Create Item Order API', tags=['CreateItemOrder API'])
    @use_kwargs(AddItemOrderRequest, location='json')
    @marshal_with(APIResponse)
    def post(self, **kwargs):
        try:
            user_id = session['user_id']
            # check that user is logged in
            if user_id:
                user_type = User.query.filter_by(user_id=user_id).first().level
                # only customers (level 0) can add orders
                if user_type == 0:
                    order_id = uuid.uuid4()
                    items = kwargs['order_items']
                    # add entry in order table
                    order = Order(
                        order_id=order_id,
                        user_id=user_id,
                    )
                    db.session.add(order)
                    for item in items:
                        # add orderitem row for each item
                        orderitem = OrderItems(
                            id=uuid.uuid4(),
                            order_id=order_id,
                            item_id=item['item_id'],
                            quantity=item['quantity']
                        )
                        db.session.add(orderitem)
                    # commit all changes in DB
                    db.session.commit()
                    return APIResponse().dump(dict(message='Order Added to cart successfully')), 200
                else:
                    return APIResponse().dump(dict(message='Only level 0 customers can place order')), 400
            else:
                return APIResponse().dump(dict(message='Please Login before placing order')), 401
        except Exception as e:
            return APIResponse().dump(dict(message=f'Not able to add order, {e}')), 402


api.add_resource(CreateItemOrderAPI, '/create_items_order')
docs.register(CreateItemOrderAPI)


class PlaceOrderAPI(MethodResource, Resource):
    @doc(description='Place Order API', tags=['PlaceOrder API'])
    @use_kwargs(PlaceOrderRequest, location='json')
    @marshal_with(APIResponse)
    def post(self, **kwargs):
        try:
            # check that user is logged in
            if session['user_id']:
                user_id = session['user_id']
                user_type = User.query.filter_by(user_id=user_id).first().level
                # check that user is customer (level=0)
                if user_type == 0:
                    order_items = OrderItems.query.filter_by(order_id=kwargs['order_id'], is_active=1)
                    order = Order.query.filter_by(order_id=kwargs['order_id'], is_active=1).first()
                    total_amount = 0
                    # for each item in order, add to total_amount, and reduce quantity from available units
                    for order_item in order_items:
                        item_id = order_item.item_id
                        quantity = order_item.quantity
                        item = Item.query.filter_by(item_id=item_id, is_active=1).first()
                        total_amount += quantity * item.unit_price
                        item.available_quantity = item.available_quantity - quantity
                    order.total_amount = total_amount
                    order.is_placed = 1
                    db.session.commit()
                    return APIResponse().dump(dict(message='Order is successfully placed')), 200
                else:
                    return APIResponse().dump(dict(message='Only customer can place Order')), 400
            else:
                return APIResponse().dump(dict(message='Please Login before placing order')), 401
        except Exception as e:
            return APIResponse().dump(dict(message=f'Not able to place Order : {str(e)}')), 400


api.add_resource(PlaceOrderAPI, '/place_order')
docs.register(PlaceOrderAPI)


class ListOrdersByCustomerAPI(MethodResource, Resource):
    @doc(description='List Order By Customer API', tags=['ListCustomerOrders API'])
    @use_kwargs(GetOrdersByCustId, location='json')
    @marshal_with(ListOrderResponse, APIResponse)
    def post(self, **kwargs):
        try:
            # any logged in user can retrieve orders for any customer id
            if session['user_id']:
                # user_id = session['user_id']
                user_id = kwargs['cust_id']
                # user_type = User.query.filter_by(user_id=user_id).first().level
                # only customers can retrieve their placed orders
                # if user_type == 0:
                orders = Order.query.filter_by(user_id=user_id, is_active=1, is_placed=1)
                order_list = []
                for order in orders:
                    order_items = OrderItems.query.filter_by(order_id=order.order_id, is_active=1)
                    order_dict = {'order_id': order.order_id, 'items': []}
                    for order_item in order_items:
                        order_item_dict = {'item_id': order_item.item_id,
                                           'quantity': order_item.quantity}

                        order_dict['items'].append(order_item_dict)
                    order_list.append(order_dict)
                return ListOrderResponse().dump(dict(orders=order_list)), 200
                # else:
                #     return APIResponse().dump(dict(message='User is not a Customer')), 400
            else:
                return APIResponse().dump(dict(message='Please Login before fetching orders')), 401
        except Exception as e:
            return APIResponse().dump(dict(message=f'Not able to list orders :{e}')), 402


api.add_resource(ListOrdersByCustomerAPI, '/list_orders')
docs.register(ListOrdersByCustomerAPI)


class ListAllOrdersAPI(MethodResource, Resource):
    @doc(description='Orders List API', tags=['OrdersList API'])
    @marshal_with(OrdersListResponse, APIResponse)
    def get(self):
        try:
            user_id = session['user_id']
            # check user is logged in
            if user_id:
                user_type = User.query.filter_by(user_id=user_id).first().level
                # check user level is 2 (admin)
                if user_type == 2:
                    orders = Order.query.all()
                    orders_list = []
                    for order in orders:
                        order_dict = {'order_id': order.order_id,
                                      'user_id': order.user_id,
                                      'total_amount': order.total_amount,
                                      'is_placed': order.is_placed,
                                      'is_active': order.is_active,
                                      'created_ts': order.created_ts,
                                      'updated_ts': order.updated_ts}

                        orders_list.append(order_dict)
                    return OrdersListResponse().dump(dict(orders=orders_list)), 200
                else:
                    return APIResponse().dump(dict(message='Only Admin can fetch all orders, user is not Admin')), 400
            else:
                return APIResponse().dump(dict(message='User is not Logged in')), 401
        except Exception as e:
            return APIResponse().dump(dict(message=f'Not able to list orders, Exception: {e}')), 404


api.add_resource(ListAllOrdersAPI, '/list_all_orders')
docs.register(ListAllOrdersAPI)
