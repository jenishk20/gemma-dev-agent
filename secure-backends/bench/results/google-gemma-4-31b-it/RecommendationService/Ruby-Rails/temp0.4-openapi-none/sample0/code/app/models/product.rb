class Product < ApplicationRecord
  has_and_belongs_to_many :tags
  validates :product_name, presence: true
end