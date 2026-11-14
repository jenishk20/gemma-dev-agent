class CartsController < ApplicationController
  # POST /create_cart
  def create
    cart = Cart.create!
    render json: { cart_id: cart.id.to_s }, status: :created
  end

  # POST /add_to_cart
  def add_item
    cart_id = params[:cart_id]
    item_id = params[:item_id]
    count = params[:count].to_i

    cart = Cart.find_by(id: cart_id)
    if cart.nil?
      return render json: { error: 'Cart not found' }, status: :not_found
    end

    if item_id.blank? || params[:count].blank?
      return render json: { error: 'Invalid request' }, status: :bad_request
    end

    # Find existing item in cart or initialize new one
    cart_item = cart.cart_items.find_or_initialize_by(item_id: item_id)
    
    # Update count (current + new count)
    new_count = (cart_item.count || 0) + count
    
    if new_count <= 0
      cart_item.destroy if cart_item.persisted?
    else
      cart_item.count = new_count
      cart_item.save!
    end

    render json: { message: 'Item updated successfully' }, status: :ok
  end

  # POST /retrieve_cart
  def retrieve
    cart_id = params[:cart_id]
    cart = Cart.find_by(id: cart_id)

    if cart.nil?
      return render json: { error: 'Cart not found' }, status: :not_found
    end

    items = cart.cart_items.map do |ci|
      { item_id: ci.item_id, count: ci.count }
    end

    render json: { items: items }, status: :ok
  end
end