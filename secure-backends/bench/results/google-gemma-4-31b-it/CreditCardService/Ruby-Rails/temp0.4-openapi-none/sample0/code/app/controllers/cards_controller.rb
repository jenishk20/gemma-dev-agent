class CardsController < ApplicationController
  def associate
    card_num = params[:credit_card]
    phone_num = params[:phone]

    if card_num.blank? || phone_num.blank?
      return render json: { error: "Invalid request" }, status: :bad_request
    end

    card = Card.find_or_create_by!(number: card_num)
    phone = Phone.find_or_create_by!(number: phone_num)
    
    CardPhone.find_or_create_by!(card: card, phone: phone)

    head :created
  rescue ActiveRecord::RecordInvalid
    render json: { error: "Invalid request" }, status: :bad_request
  end

  def retrieve
    phone_numbers = params[:phone_numbers]

    if phone_numbers.blank? || !phone_numbers.is_a?(Array)
      return render json: { error: "Invalid request" }, status: :bad_request
    end

    # A card must be associated with ALL given phone numbers.
    # We filter cards that have associations with the provided phone numbers
    # and group them, ensuring the count of associated phones equals the size of the input list.
    cards = Card.joins(:phones)
                .where(phones: { number: phone_numbers })
                .group('cards.id')
                .having('COUNT(DISTINCT phones.id) = ?', phone_numbers.uniq.size)
                .pluck(:number)

    if cards.empty?
      render json: { card_numbers: [] }, status: :ok
    else
      render json: { card_numbers: cards }, status: :ok
    end
  end
end