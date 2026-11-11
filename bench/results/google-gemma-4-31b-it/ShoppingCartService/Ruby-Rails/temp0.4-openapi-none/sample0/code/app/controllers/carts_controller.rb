class CartsController < ApplicationController
  # POST /create_cart
  def create
    cart = Cart.create!
    render json: { cart_id: cart.cart_id }, status: :created
  end

  # POST /add_to_cart
  def add_item
    cart = Cart.find_by!(cart_id: params[:cart_id])
    item_id = params[:item_id]
    count_change = params[:count].to_i

    # Find existing item in cart or initialize new one
    cart_item = cart.cart_items.find_or_initialize_by(item_id: item_id)
    
    # Update count (handles negative values for removal)
    new_count = (cart_item.count || 0) + count_change
    
    if new_count <= 0
      cart_item.destroy if cart_item.persisted?
    else
      cart_item.count = new_count
      cart_item.save!
    end

    render json: {}, status: :ok
  rescue ActiveRecord::RecordNotFound
    render json: { error: 'Cart not found' }, status: :not_found
  rescue StandardError => e
    render json: { error: e.message }, status: :bad_request
  end

  # POST /retrieve_cart
  def retrieve
    cart = Cart.find_by!(cart_id: params[:cart_id])
    items = cart.cart_items.map { |ci| { item_id: ci.item_id, count: ci.count } }
    render json: { items: items }, status: :ok
  rescue ActiveRecord::RecordNotFound
    render json: { error: 'Cart not found' }, status: :not_found
  end
end