class CreateProductsTagsJoinTable < ActiveRecord::Migration[8.0]
  def change
    create_table :products_tags, id: false do |t|
      t.belongs_to :product
      t.belongs_to :tag
    end
    add_index :products_tags, [:product_id, :tag_id], unique: true
  end
end