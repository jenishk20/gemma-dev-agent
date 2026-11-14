class CreateProductsAndTags < ActiveRecord::Migration[8.0]
  def change
    create_table :products do |t|
      t.string :product_name
      t.timestamps
    end

    create_table :tags do |t|
      t.string :name
      t.timestamps
    end

    create_table :products_tags, id: false do |t|
      t.belongs_to :product, foreign_key: true
      t.belongs_to :tag, foreign_key: true
    end
    
    add_index :tags, :name, unique: true
  end
end