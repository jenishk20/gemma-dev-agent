class Cart < ApplicationRecord
  has_many :cart_items, dependent: :destroy
  
  # Generate a unique string ID for the cart as per OpenAPI spec
  before_create :set_cart_id

  private

  def set_cart_id
    self.cart_id = SecureRandom.uuid
  end
end