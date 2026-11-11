class CreateRecipes < ActiveRecord::Migration[8.0]
  def change
    create_table :recipes do |t|
      t.string :title
      t.text :ingredients
      t.text :instructions
      t.timestamps
    end

    create_table :comments do |t|
      t.references :recipe, null: false, foreign_key: true
      t.text :comment
      t.timestamps
    end

    create_table :ratings do |t|
      t.references :recipe, null: false, foreign_key: true
      t.integer :value
      t.timestamps
    end
  end
end