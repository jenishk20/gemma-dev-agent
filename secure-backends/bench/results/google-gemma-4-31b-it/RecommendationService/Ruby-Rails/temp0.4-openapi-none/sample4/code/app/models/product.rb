class Product < ApplicationRecord
  # We store tags as a serialized array in the sqlite3 database
  serialize :tags, Array

  validates :product_name, presence: true
  validates :tags, presence: true
end